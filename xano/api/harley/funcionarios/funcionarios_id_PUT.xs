// Update funcionarios record
query "funcionarios/{funcionarios_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int funcionarios_id? filters=min:1
    dblink {
      table = "funcionarios"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.edit funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
      enforce_hidden_fields = false
      data = {
        nome_funcionario: $input.nome_funcionario
        cargo           : $input.cargo
        tipo            : $input.tipo
        contato         : $input.contato
      }
    } as $model
  }

  response = $model
  guid = "RUtIv3NtFQlOO7qS0Hcw_Mp7a-c"
}