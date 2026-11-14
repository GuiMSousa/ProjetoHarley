// Registra uma entrada de mercadoria com seus itens e incrementa o estoque atomicamente.
// Os itens são gravados em ordem crescente de produto, pelo banco (Change 16).
// O saldo muda somente por Estoque/movimentar_estoque (ENTRADA), que grava o livro de
// movimentações e serializa movimentações concorrentes do mesmo produto (Change 7).
// As validações rodam antes da transação, com mensagens específicas; dentro dela ficam só as
// gravações. Uma corrida (mesmo documento ou mesmo produto ao mesmo tempo) viola um índice
// único, desfaz tudo e responde 400 com a mensagem de conflito (saneamento pós-Change 9).
query entrada_mercadoria verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int id_fornecedor filters=min:1
    text numero_documento filters=trim
    object[] itens {
      schema {
        int id_produto filters=min:1
        int quantidade filters=min:1
        decimal valor_unitario filters=min:0.01
      }
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
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

    precondition (($input.numero_documento|strlen) > 0) {
      error_type = "inputerror"
      error = "Informe o número do documento."
    }

    precondition (($input.itens|count) > 0) {
      error_type = "inputerror"
      error = "Informe ao menos um item na entrada."
    }

    // Teto da nota (Change 16): uma entrada grande deixa a transação e as travas de estoque abertas.
    precondition (($input.itens|count) <= 50) {
      error_type = "inputerror"
      error = "A entrada pode ter no máximo 50 itens."
    }

    var $ids_produto {
      value = $input.itens|map:$$.id_produto
    }

    precondition (($ids_produto|count) == ($ids_produto|unique|count)) {
      error_type = "inputerror"
      error = "Um mesmo produto não pode aparecer mais de uma vez na entrada."
    }

    var $valor_total {
      value = 0
    }

    foreach ($input.itens) {
      each as $item_valor {
        var.update $valor_total {
          value = $valor_total + ($item_valor.quantidade * $item_valor.valor_unitario)
        }
      }
    }

    db.get fornecedores {
      field_name = "id"
      field_value = $input.id_fornecedor
      output = ["id", "ativo"]
    } as $fornecedor

    precondition ($fornecedor != null && $fornecedor.ativo != false) {
      error_type = "inputerror"
      error = "Fornecedor inativo ou inexistente."
    }

    db.query entrada_mercadoria {
      where = $db.entrada_mercadoria.id_fornecedor == $input.id_fornecedor && $db.entrada_mercadoria.numero_documento == $input.numero_documento
      return = {type: "exists"}
    } as $documento_existente

    precondition (!$documento_existente) {
      error_type = "inputerror"
      error = "Este documento já foi registrado para o fornecedor."
    }

    // Produtos lidos numa só consulta (Change 16) e conferidos na ordem da nota.
    db.query produtos {
      where = $db.produtos.id in $ids_produto
      output = ["id", "ativo"]
      return = {type: "list"}
    } as $produtos

    var $produto {
      value = null
    }

    foreach ($input.itens) {
      each as $item_validado {
        var.update $produto {
          value = $produtos|find:$$.id == $item_validado.id_produto
        }

        precondition ($produto != null && $produto.ativo != false) {
          error_type = "inputerror"
          error = "Produto inativo ou inexistente: " ~ $item_validado.id_produto
        }
      }
    }

    try_catch {
      try {
        db.transaction {
          stack {
            db.add entrada_mercadoria {
              data = {
                id_fornecedor   : $input.id_fornecedor
                numero_documento: $input.numero_documento
                id_funcionario  : $auth_user.id_funcionario
                data_entrada    : now
                valor_total     : $valor_total
              }
            } as $entrada

            // Ordem crescente de id, pelo banco (Change 16): a mesma da venda de balcão e do
            // cancelamento de OS, para que operações simultâneas travem os produtos na mesma ordem.
            db.query produtos {
              where = $db.produtos.id in $ids_produto
              sort = {id: "asc"}
              output = ["id"]
              return = {type: "list"}
            } as $produtos_ordenados

            // Um produto que sumisse daqui ficaria fora da nota sem erro.
            precondition (($produtos_ordenados|count) == ($ids_produto|count)) {
              error_type = "inputerror"
              error = "Produto inativo ou inexistente."
            }

            var $item {
              value = null
            }

            foreach ($produtos_ordenados) {
              each as $produto_ordenado {
                var.update $item {
                  value = $input.itens|find:$$.id_produto == $produto_ordenado.id
                }

                db.add itens_compra_estoque {
                  data = {
                    id_entrada    : $entrada.id
                    id_produto    : $item.id_produto
                    quantidade    : $item.quantidade
                    valor_unitario: $item.valor_unitario
                  }
                } as $item_compra

                function.run "Estoque/movimentar_estoque" {
                  input = {
                    id_produto    : $item.id_produto
                    tipo          : "ENTRADA"
                    quantidade    : $item.quantidade
                    id_funcionario: $auth_user.id_funcionario
                    id_entrada    : $entrada.id
                  }
                } as $movimento
              }
            }
          }
        }
      }

      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "A entrada não foi registrada: o documento ou o estoque foram alterados por outra operação. Atualize e tente novamente."
        }
      }
    }

    function.run "Estoque/detalhe_entrada" {
      input = {entrada_id: $entrada.id}
    } as $detalhe
  }

  response = $detalhe
  guid = "yrfUTmszZdAKABXHdOqprSIglHw"
}
