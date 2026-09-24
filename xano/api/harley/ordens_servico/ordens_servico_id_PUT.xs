// Update ordens_servico record
query "ordens_servico/{ordens_servico_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id? filters=min:1
    dblink {
      table = "ordens_servico"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check
      db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id_funcionario"]
    } as $auth_user
      db.edit ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
      enforce_hidden_fields = false
      data = {
        id_moto_cliente: $input.id_moto_cliente
        id_funcionario : $auth_user.id_funcionario
        data_abertura  : $input.data_abertura
        status         : $input.status
      }
    } as $model
  }

  response = $model
  guid = "zW1uaingCXiItr3hGYlHC4-hHW0"
}