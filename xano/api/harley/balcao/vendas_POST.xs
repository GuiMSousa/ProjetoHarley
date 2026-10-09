// Venda de peças no balcão (Change 11, GERENTE ou VENDEDOR). Grava numa única transação:
//   1. a transação BALCAO (cliente opcional: sem ele, consumidor final);
//   2. os itens, com o preço fotografado de produtos.preco_venda (o payload não traz preço);
//   3. a saída de estoque de cada item por Estoque/movimentar_estoque (SAIDA_VENDA).
// O funcionário vem do usuário autenticado ($auth.id -> user.id_funcionario), nunca do payload.
// Idempotência: a chave_venda (UUID do carrinho) já gravada devolve o recibo existente, sem nova
// baixa nem nova receita. As validações rodam antes da transação, com mensagens específicas;
// dentro dela os preços são relidos e o total é conferido de novo. Uma corrida (estoque, preço
// ou mesma chave) viola um índice único ou uma precondição, desfaz tudo e responde 400 com a
// mensagem de conflito. Os produtos são gravados em ordem crescente de id, a mesma do
// cancelamento de OS, para que operações simultâneas travem os produtos na mesma ordem.
query "balcao/vendas" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    // UUID do carrinho, gerado pelo Reflex e mantido nas novas tentativas.
    text chave_venda filters=trim|max:64

    // Opcional: sem cliente, a venda é de consumidor final.
    int? id_cliente? filters=min:1

    // Total exibido ao vendedor; o Xano recalcula e recusa a venda se divergir.
    decimal total_esperado filters=min:0.01

    object[] itens {
      schema {
        int id_produto filters=min:1
        int quantidade filters=min:1
      }
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
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

    precondition (($input.chave_venda|strlen) > 0) {
      error_type = "inputerror"
      error = "Chave da venda ausente. Atualize a página e tente novamente."
    }

    // Repetição da mesma chave (resposta perdida, novo clique): devolve a venda já gravada.
    db.query itens_transacao {
      where = $db.itens_transacao.chave_venda == $input.chave_venda
      output = ["id_transacao"]
      return = {type: "single"}
    } as $venda_existente

    var $id_transacao {
      value = null
    }

    conditional {
      if ($venda_existente != null) {
        var.update $id_transacao {
          value = $venda_existente.id_transacao
        }
      }
    }

    conditional {
      if ($id_transacao == null) {
        precondition (($input.itens|count) > 0) {
          error_type = "inputerror"
          error = "Informe ao menos um item."
        }

        precondition (($input.itens|count) <= 30) {
          error_type = "inputerror"
          error = "A venda pode ter no máximo 30 itens."
        }

        var $ids_produto {
          value = $input.itens|map:$$.id_produto
        }

        precondition (($ids_produto|count) == ($ids_produto|unique|count)) {
          error_type = "inputerror"
          error = "Um mesmo produto não pode aparecer mais de uma vez na venda."
        }

        conditional {
          if ($input.id_cliente != null) {
            db.get clientes {
              field_name = "id"
              field_value = $input.id_cliente
              output = ["id", "ativo"]
            } as $cliente

            precondition ($cliente != null && $cliente.ativo != false) {
              error_type = "inputerror"
              error = "Cliente inativo ou inexistente."
            }
          }
        }

        // Pré-checagens fora da transação: dão as mensagens específicas de produto e saldo.
        var $total_previo {
          value = 0
        }

        // Quantidade pedida por produto (chave = id em texto), usada dentro da transação.
        var $quantidades {
          value = {}
        }

        foreach ($input.itens) {
          each as $item_pedido {
            db.get produtos {
              field_name = "id"
              field_value = $item_pedido.id_produto
              output = ["id", "codigo", "estoque_qtd", "preco_venda", "ativo"]
            } as $produto_previo

            precondition ($produto_previo != null && $produto_previo.ativo != false) {
              error_type = "inputerror"
              error = "Produto inativo ou inexistente: " ~ $item_pedido.id_produto
            }

            precondition (($produto_previo.estoque_qtd ?? 0) >= $item_pedido.quantidade) {
              error_type = "inputerror"
              error = "Saldo insuficiente para " ~ $produto_previo.codigo ~ ": disponível " ~ ($produto_previo.estoque_qtd ?? 0) ~ ", solicitado " ~ $item_pedido.quantidade ~ "."
            }

            var.update $total_previo {
              value = $total_previo + (($item_pedido.quantidade * $produto_previo.preco_venda)|round:2)
            }

            var.update $quantidades {
              value = $quantidades|set:($item_pedido.id_produto|to_text):$item_pedido.quantidade
            }
          }
        }

        // O total mostrado ao vendedor precisa ser o que o cliente vai pagar.
        precondition (($total_previo|round:2) == ($input.total_esperado|round:2)) {
          error_type = "inputerror"
          error = "Os preços mudaram desde que o carrinho foi montado: o total agora é R$ " ~ ($total_previo|number_format:2:",":".") ~ ". Revise o carrinho."
        }

        try_catch {
          try {
            db.transaction {
              stack {
                // Ordem crescente de id, pelo banco (a mesma do cancelamento de OS).
                db.query produtos {
                  where = $db.produtos.id in $ids_produto
                  sort = {id: "asc"}
                  output = ["id", "preco_venda", "ativo"]
                  return = {type: "list"}
                } as $produtos

                precondition (($produtos|count) == ($ids_produto|count)) {
                  error_type = "inputerror"
                  error = "Produto inativo ou inexistente."
                }

                var $linhas {
                  value = []
                }

                var $linha {
                  value = {}
                }

                var $total_atual {
                  value = 0
                }

                foreach ($produtos) {
                  each as $produto_atual {
                    precondition ($produto_atual.ativo != false) {
                      error_type = "inputerror"
                      error = "Produto inativo ou inexistente."
                    }

                    var.update $linha {
                      value = {
                        id_produto      : $produto_atual.id
                        quantidade      : $quantidades|get:($produto_atual.id|to_text)
                        valor_unitario  : $produto_atual.preco_venda
                        valor_total_item: (($quantidades|get:($produto_atual.id|to_text)) * $produto_atual.preco_venda)|round:2
                      }
                    }

                    var.update $linhas {
                      value = $linhas|push:$linha
                    }

                    var.update $total_atual {
                      value = $total_atual + $linha.valor_total_item
                    }
                  }
                }

                // Um preço mudou entre a pré-checagem e a transação: cai no catch.
                precondition (($total_atual|round:2) == ($input.total_esperado|round:2)) {
                  error_type = "inputerror"
                  error = "Os preços mudaram durante o fechamento."
                }

                db.add transacoes {
                  data = {
                    tipo_transacao: "BALCAO"
                    id_funcionario: $auth_user.id_funcionario
                    id_cliente    : $input.id_cliente
                    data_transacao: now
                    valor_total   : $total_atual|round:2
                  }
                } as $transacao

                foreach ($linhas) {
                  each as $linha_venda {
                    db.add itens_transacao {
                      data = {
                        id_transacao    : $transacao.id
                        id_produto      : $linha_venda.id_produto
                        quantidade      : $linha_venda.quantidade
                        valor_unitario  : $linha_venda.valor_unitario
                        valor_total_item: $linha_venda.valor_total_item
                        chave_venda     : $input.chave_venda
                        created_at      : now
                      }
                    } as $item_venda

                    function.run "Estoque/movimentar_estoque" {
                      input = {
                        id_produto    : $linha_venda.id_produto
                        tipo          : "SAIDA_VENDA"
                        quantidade    : $linha_venda.quantidade
                        id_funcionario: $auth_user.id_funcionario
                        id_transacao  : $transacao.id
                      }
                    } as $movimento
                  }
                }

                var.update $id_transacao {
                  value = $transacao.id
                }
              }
            }
          }

          catch {
            precondition (false) {
              error_type = "inputerror"
              error = "A venda não foi registrada: o estoque ou os preços mudaram durante o fechamento. Revise o carrinho e tente novamente."
            }
          }
        }
      }
    }

    function.run "Balcao/detalhe_venda" {
      input = {id_transacao: $id_transacao}
    } as $recibo
  }

  response = $recibo
  guid = "SSMbdAEuy-qt2pVSe_wdNS_BMgw"
}
