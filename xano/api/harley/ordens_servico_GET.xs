// Lista ordens de serviço enriquecidas; filtros opcionais por status e por moto do cliente.
query ordens_servico verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    enum? status? {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    int? id_moto_cliente? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check

    db.query ordens_servico {
      join = {
        motos_clientes: {
          table: "motos_clientes"
          type : "left"
          where: $db.ordens_servico.id_moto_cliente == $db.motos_clientes.id
        }
        clientes: {
          table: "clientes"
          type : "left"
          where: $db.motos_clientes.id_cliente == $db.clientes.id
        }
      }

      where = $db.ordens_servico.status ==? $input.status && $db.ordens_servico.id_moto_cliente ==? $input.id_moto_cliente
      eval = {
        placa       : $db.motos_clientes.placa
        modelo      : $db.motos_clientes.modelo
        nome_cliente: $db.clientes.nome_cliente
      }

      sort = {data_abertura: "desc"}
      return = {type: "list"}
    } as $ordens

    // Autor e mecânico vêm da mesma tabela: um mapa com uma única consulta evita N+1.
    db.query funcionarios {
      return = {type: "list"}
    } as $funcionarios

    var $model {
      value = []
    }

    var $autor {
      value = null
    }

    var $mecanico {
      value = null
    }

    foreach ($ordens) {
      each as $ordem {
        var.update $autor {
          value = $funcionarios|find:$$.id == $ordem.id_funcionario
        }

        var.update $mecanico {
          value = $funcionarios|find:$$.id == $ordem.id_mecanico
        }

        var.update $model {
          value = $model|push:($ordem|set:"nome_funcionario":$autor.nome_funcionario|set:"nome_mecanico":$mecanico.nome_funcionario)
        }
      }
    }
  }

  response = $model
  guid = "ejDbmcP8h6RVydMZ06OpqGhtIO0"
}
