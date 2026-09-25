// Remove um item de uma OS ABERTA ou EM_ANDAMENTO. Peças com baixa de estoque voltam ao
// estoque na mesma transação (ESTORNO_OS); serviços e itens legados não movimentam estoque.
// Concorrência: trava a linha da OS (atualizado_em) antes de reler status e item.
query "ordens_servico/{ordens_servico_id}/itens/{item_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id filters=min:1
    int item_id filters=min:1
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

    db.get ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
      output = ["id", "status"]
    } as $os

    precondition ($os != null) {
      error_type = "notfound"
      error = "Ordem de serviço não encontrada."
    }

    db.get itens_ordem_servico {
      field_name = "id"
      field_value = $input.item_id
      output = ["id", "id_os"]
    } as $item_previo

    precondition ($item_previo != null && $item_previo.id_os == $input.ordens_servico_id) {
      error_type = "notfound"
      error = "Item não encontrado nesta OS."
    }

    precondition ($os.status == "ABERTA" || $os.status == "EM_ANDAMENTO") {
      error_type = "inputerror"
      error = "OS encerrada não permite alterar itens."
    }

    try_catch {
      try {
        db.transaction {
          stack {
            // Trava a linha da OS antes de reler status e item.
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

            db.get itens_ordem_servico {
              field_name = "id"
              field_value = $input.item_id
              output = ["id", "id_os", "id_produto", "quantidade", "estoque_baixado"]
            } as $item

            precondition ($item != null && $item.id_os == $input.ordens_servico_id) {
              error_type = "notfound"
              error = "Item não encontrado nesta OS."
            }

            conditional {
              if ($item.estoque_baixado == true) {
                function.run "Estoque/movimentar_estoque" {
                  input = {
                    id_produto    : $item.id_produto
                    tipo          : "ESTORNO_OS"
                    quantidade    : $item.quantidade
                    id_funcionario: $auth_user.id_funcionario
                    id_os         : $input.ordens_servico_id
                    id_item_os    : $item.id
                  }
                } as $movimento
              }
            }

            db.del itens_ordem_servico {
              field_name = "id"
              field_value = $input.item_id
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
  guid = "hAnjCagPhKR8D5HdgYrdNm4Uo2g"
}
