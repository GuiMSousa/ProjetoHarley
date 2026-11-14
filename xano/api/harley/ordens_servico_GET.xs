// Lista ordens de serviço enriquecidas; filtros opcionais por status e por moto do cliente.
// Autor e mecânico vêm da mesma tabela, por dois apelidos de join (Change 16): antes, a tabela
// inteira de funcionários era lida e percorrida para cada OS.
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
        autor: {
          table: "funcionarios"
          type : "left"
          where: $db.ordens_servico.id_funcionario == $db.autor.id
        }
        mecanico: {
          table: "funcionarios"
          type : "left"
          where: $db.ordens_servico.id_mecanico == $db.mecanico.id
        }
      }

      where = $db.ordens_servico.status ==? $input.status && $db.ordens_servico.id_moto_cliente ==? $input.id_moto_cliente
      eval = {
        placa           : $db.motos_clientes.placa
        modelo          : $db.motos_clientes.modelo
        nome_cliente    : $db.clientes.nome_cliente
        nome_funcionario: $db.autor.nome_funcionario
        nome_mecanico   : $db.mecanico.nome_funcionario
      }

      sort = {data_abertura: "desc"}
      return = {type: "list"}
    } as $ordens
  }

  response = $ordens
  guid = "ejDbmcP8h6RVydMZ06OpqGhtIO0"
}
