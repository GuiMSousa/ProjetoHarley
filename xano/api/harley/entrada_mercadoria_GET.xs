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

    // Os filtros só recebem variáveis: chave e contagem são calculadas antes, em passos próprios.
    // Uma expressão entre parênteses como argumento de get/set passava no validador e falhava em
    // execução com HTTP 500 "Invalid expression" assim que havia itens (2026-11-18).
    var $quantidades {
      value = {}
    }

    var $chave {
      value = ""
    }

    var $quantidade {
      value = 0
    }

    foreach ($itens) {
      each as $item {
        var.update $chave {
          value = "e" ~ $item.id_entrada
        }

        var.update $quantidade {
          value = $quantidades|get:$chave:0
        }

        var.update $quantidade {
          value = $quantidade + 1
        }

        var.update $quantidades {
          value = $quantidades|set:$chave:$quantidade
        }
      }
    }

    var $model {
      value = []
    }

    var $linha {
      value = {}
    }

    foreach ($entradas) {
      each as $entrada {
        var.update $chave {
          value = "e" ~ $entrada.id
        }

        var.update $quantidade {
          value = $quantidades|get:$chave:0
        }

        var.update $linha {
          value = $entrada|set:"quantidade_itens":$quantidade
        }

        var.update $model {
          value = $model|push:$linha
        }
      }
    }
  }

  response = $model
  guid = "TfNTbEqZ2VB_fjEZK9XJlNQtdKo"
}
