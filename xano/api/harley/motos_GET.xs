// Unidades do estoque de motos para vendedores e gerentes (Change 8), com filtros por status e
// modelo. Nomes de modelo, cliente e vendedor vêm de joins à esquerda numa única consulta
// (Change 16): sem ler tabelas inteiras e sem acessar campos de um registro ausente.
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
      join = {
        modelos_moto: {
          table: "modelos_moto"
          type : "left"
          where: $db.motos.id_modelo == $db.modelos_moto.id
        }
        clientes: {
          table: "clientes"
          type : "left"
          where: $db.motos.clientes_id == $db.clientes.id
        }
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.motos.id_vendedor_reserva == $db.funcionarios.id
        }
      }

      where = $db.motos.status ==? $input.status && $db.motos.id_modelo ==? $input.id_modelo
      eval = {
        nome_modelo  : $db.modelos_moto.nome_modelo
        familia      : $db.modelos_moto.familia
        variacoes_cor: $db.modelos_moto.variacoes_cor
        nome_cliente : $db.clientes.nome_cliente
        nome_vendedor: $db.funcionarios.nome_funcionario
      }

      sort = {id: "desc"}
      return = {type: "list"}
    } as $motos
  }

  response = $motos
  guid = "MmiokOmzzZysN1u43xASFIsdQm0"
}
