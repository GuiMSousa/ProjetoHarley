// Inclui uma peça ou um serviço numa OS ABERTA ou EM_ANDAMENTO.
// Peça: preço vindo de produtos.preco_venda (fotografia) e baixa de estoque na mesma
// transação, via Estoque/movimentar_estoque (SAIDA_OS). Serviço: valor informado, sem estoque.
// Concorrência: a transação começa travando a linha da OS (atualizado_em) e só então relê o
// status, o que serializa inclusões, remoções e transições da mesma OS; o saldo é serializado
// pelo índice único do livro de movimentações.
query "ordens_servico/{ordens_servico_id}/itens" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id filters=min:1
    enum tipo_item {
      values = ["PECA", "SERVICO"]
    }

    // Obrigatório para PECA; ignorado para SERVICO.
    int? id_produto? filters=min:1

    // Obrigatória para SERVICO; ignorada para PECA.
    text? descricao? filters=trim

    int quantidade filters=min:1

    // Obrigatório para SERVICO; ignorado para PECA (o preço vem do produto).
    decimal? valor_unitario? filters=min:0.01
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id_funcionario"]
    } as $auth_user

    precondition ($auth_user.id_funcionario != null) {
      error_type = "accessdenied"
      error = "Seu usuário não está vinculado a um funcionário."
    }

    // Pré-checagens fora da transação: dão as mensagens específicas.
    db.get ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
      output = ["id", "status"]
    } as $os

    precondition ($os != null) {
      error_type = "notfound"
      error = "Ordem de serviço não encontrada."
    }

    precondition ($os.status == "ABERTA" || $os.status == "EM_ANDAMENTO") {
      error_type = "inputerror"
      error = "OS encerrada não permite alterar itens."
    }

    conditional {
      if ($input.tipo_item == "PECA") {
        precondition ($input.id_produto != null) {
          error_type = "inputerror"
          error = "Selecione o produto."
        }

        db.get produtos {
          field_name = "id"
          field_value = $input.id_produto
          output = ["id", "codigo", "estoque_qtd", "ativo"]
        } as $produto_previo

        precondition ($produto_previo != null && $produto_previo.ativo != false) {
          error_type = "inputerror"
          error = "Produto inativo ou inexistente."
        }

        db.query itens_ordem_servico {
          where = $db.itens_ordem_servico.id_os == $input.ordens_servico_id && $db.itens_ordem_servico.id_produto == $input.id_produto
          return = {type: "exists"}
        } as $repetido

        precondition (!$repetido) {
          error_type = "inputerror"
          error = "Este produto já está na OS. Remova o item para alterar a quantidade."
        }

        precondition (($produto_previo.estoque_qtd ?? 0) >= $input.quantidade) {
          error_type = "inputerror"
          error = "Saldo insuficiente para " ~ $produto_previo.codigo ~ ": disponível " ~ ($produto_previo.estoque_qtd ?? 0) ~ ", solicitado " ~ $input.quantidade ~ "."
        }
      }

      else {
        precondition ((($input.descricao ?? "")|strlen) > 0) {
          error_type = "inputerror"
          error = "Informe a descrição do serviço."
        }

        precondition ($input.valor_unitario != null) {
          error_type = "inputerror"
          error = "Informe o valor do serviço."
        }
      }
    }

    try_catch {
      try {
        db.transaction {
          stack {
            // Trava a linha da OS antes de reler o status.
            db.edit ordens_servico {
              field_name = "id"
              field_value = $input.ordens_servico_id
              data = {atualizado_em: now}
            } as $os_travada

            db.get ordens_servico {
              field_name = "id"
              field_value = $input.ordens_servico_id
              output = ["id", "status"]
            } as $os_atual

            precondition ($os_atual.status == "ABERTA" || $os_atual.status == "EM_ANDAMENTO") {
              error_type = "inputerror"
              error = "OS encerrada não permite alterar itens."
            }

            conditional {
              if ($input.tipo_item == "PECA") {
                db.get produtos {
                  field_name = "id"
                  field_value = $input.id_produto
                  output = ["id", "preco_venda"]
                } as $produto

                precondition ($produto != null) {
                  error_type = "inputerror"
                  error = "Produto inativo ou inexistente."
                }

                db.query itens_ordem_servico {
                  where = $db.itens_ordem_servico.id_os == $input.ordens_servico_id && $db.itens_ordem_servico.id_produto == $input.id_produto
                  return = {type: "exists"}
                } as $repetido_na_transacao

                precondition (!$repetido_na_transacao) {
                  error_type = "inputerror"
                  error = "Este produto já está na OS. Remova o item para alterar a quantidade."
                }

                db.add itens_ordem_servico {
                  data = {
                    id_os           : $input.ordens_servico_id
                    id_produto      : $input.id_produto
                    tipo_item       : "PECA"
                    quantidade      : $input.quantidade
                    valor_unitario  : $produto.preco_venda
                    valor_total_item: ($input.quantidade * $produto.preco_venda)|round:2
                    estoque_baixado : true
                    id_funcionario  : $auth_user.id_funcionario
                    created_at      : now
                  }
                } as $item_peca

                function.run "Estoque/movimentar_estoque" {
                  input = {
                    id_produto    : $input.id_produto
                    tipo          : "SAIDA_OS"
                    quantidade    : $input.quantidade
                    id_funcionario: $auth_user.id_funcionario
                    id_os         : $input.ordens_servico_id
                    id_item_os    : $item_peca.id
                  }
                } as $movimento
              }

              else {
                db.add itens_ordem_servico {
                  data = {
                    id_os           : $input.ordens_servico_id
                    tipo_item       : "SERVICO"
                    descricao       : $input.descricao
                    quantidade      : $input.quantidade
                    valor_unitario  : $input.valor_unitario
                    valor_total_item: ($input.quantidade * $input.valor_unitario)|round:2
                    estoque_baixado : false
                    id_funcionario  : $auth_user.id_funcionario
                    created_at      : now
                  }
                } as $item_servico
              }
            }

            function.run "Oficina/totais_os" {
              input = {os_id: $input.ordens_servico_id}
            } as $totais

            db.edit ordens_servico {
              field_name = "id"
              field_value = $input.ordens_servico_id
              data = {
                valor_pecas   : $totais.valor_pecas
                valor_servicos: $totais.valor_servicos
                valor_total   : $totais.valor_total
              }
            } as $os_totalizada
          }
        }
      }

      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "O estoque ou a OS foram alterados por outra operação. Atualize e tente novamente."
        }
      }
    }

    function.run "Oficina/detalhe_os" {
      input = {os_id: $input.ordens_servico_id}
    } as $detalhe
  }

  response = $detalhe
  guid = "x0DaBntl8Z4brnkhqROQdo1ptsk"
}
