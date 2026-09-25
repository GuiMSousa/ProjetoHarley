// Registra uma entrada de mercadoria com seus itens e incrementa o estoque atomicamente.
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

    db.transaction {
      stack {
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

        db.add entrada_mercadoria {
          data = {
            id_fornecedor   : $input.id_fornecedor
            numero_documento: $input.numero_documento
            id_funcionario  : $auth_user.id_funcionario
            data_entrada    : now
            valor_total     : $valor_total
          }
        } as $entrada

        foreach ($input.itens) {
          each as $item {
            db.get produtos {
              field_name = "id"
              field_value = $item.id_produto
              output = ["id", "codigo", "estoque_qtd", "ativo"]
            } as $produto

            precondition ($produto != null && $produto.ativo != false) {
              error_type = "inputerror"
              error = "Produto inativo ou inexistente: " ~ $item.id_produto
            }

            db.add itens_compra_estoque {
              data = {
                id_entrada    : $entrada.id
                id_produto    : $item.id_produto
                quantidade    : $item.quantidade
                valor_unitario: $item.valor_unitario
              }
            } as $item_compra

            db.edit produtos {
              field_name = "id"
              field_value = $produto.id
              data = {
                estoque_qtd: ($produto.estoque_qtd ?? 0) + $item.quantidade
              }
            } as $produto_atualizado
          }
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
