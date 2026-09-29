// Unidades do estoque de motos para vendedores e gerentes (Change 8), com filtros por status e
// modelo. Nomes de modelo, cliente e vendedor vêm de uma consulta por tabela (sem N+1).
query motos verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    enum? status? {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    int? id_modelo? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check

    db.query motos {
      where = $db.motos.status ==? $input.status && $db.motos.id_modelo ==? $input.id_modelo
      sort = {id: "desc"}
      return = {type: "list"}
    } as $motos

    db.query modelos_moto {
      output = ["id", "nome_modelo", "familia", "variacoes_cor"]
      return = {type: "list"}
    } as $modelos

    db.query clientes {
      output = ["id", "nome_cliente"]
      return = {type: "list"}
    } as $clientes

    db.query funcionarios {
      output = ["id", "nome_funcionario"]
      return = {type: "list"}
    } as $funcionarios

    var $lista {
      value = []
    }

    var $modelo {
      value = null
    }

    var $cliente {
      value = null
    }

    var $vendedor {
      value = null
    }

    foreach ($motos) {
      each as $moto {
        var.update $modelo {
          value = $modelos|find:$$.id == $moto.id_modelo
        }

        var.update $cliente {
          value = $clientes|find:$$.id == $moto.clientes_id
        }

        var.update $vendedor {
          value = $funcionarios|find:$$.id == $moto.id_vendedor_reserva
        }

        var.update $lista {
          value = $lista|push:($moto|set:"nome_modelo":$modelo.nome_modelo|set:"familia":$modelo.familia|set:"variacoes_cor":$modelo.variacoes_cor|set:"nome_cliente":$cliente.nome_cliente|set:"nome_vendedor":$vendedor.nome_funcionario)
        }
      }
    }
  }

  response = $lista
  guid = "MmiokOmzzZysN1u43xASFIsdQm0"
}
