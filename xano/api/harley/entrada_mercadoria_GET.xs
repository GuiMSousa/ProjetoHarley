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

    // Itens contados numa única consulta, agrupados por entrada em memória (Change 16): antes era
    // uma consulta de contagem por entrada. A chave leva o prefixo "e" porque um caminho só com
    // dígitos pode ser lido como índice de array.
    // shortcut: lê o id_entrada de todos os itens; paginar junto com a lista de entradas se ela crescer.
    db.query itens_compra_estoque {
      output = ["id_entrada"]
      return = {type: "list"}
    } as $itens

    var $quantidades {
      value = {}
    }

    foreach ($itens) {
      each as $item {
        var.update $quantidades {
          value = $quantidades|set:("e" ~ $item.id_entrada):(($quantidades|get:("e" ~ $item.id_entrada):0) + 1)
        }
      }
    }

    var $model {
      value = []
    }

    foreach ($entradas) {
      each as $entrada {
        var.update $model {
          value = $model|push:($entrada|set:"quantidade_itens":($quantidades|get:("e" ~ $entrada.id):0))
        }
      }
    }
  }

  response = $model
  guid = "TfNTbEqZ2VB_fjEZK9XJlNQtdKo"
}
