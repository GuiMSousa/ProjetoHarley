// Query all entrada_mercadoria records with supplier, employee and item count
query entrada_mercadoria verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check

    db.query entrada_mercadoria {
      join = {
        fornecedores: {
          table: "fornecedores"
          type : "left"
          where: $db.entrada_mercadoria.id_fornecedor == $db.fornecedores.id
        }
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.entrada_mercadoria.id_funcionario == $db.funcionarios.id
        }
      }

      eval = {
        nome_fornecedor : $db.fornecedores.nome_fornecedor
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      sort = {data_entrada: "desc"}
      return = {type: "list"}
    } as $entradas

    var $model {
      value = []
    }

    foreach ($entradas) {
      each as $entrada {
        db.query itens_compra_estoque {
          where = $db.itens_compra_estoque.id_entrada == $entrada.id
          return = {type: "count"}
        } as $quantidade_itens

        var.update $model {
          value = $model|push:($entrada|set:"quantidade_itens":$quantidade_itens)
        }
      }
    }
  }

  response = $model
  guid = "TfNTbEqZ2VB_fjEZK9XJlNQtdKo"
}
