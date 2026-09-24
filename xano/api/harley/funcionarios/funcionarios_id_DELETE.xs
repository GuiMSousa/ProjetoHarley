// Delete funcionarios record
query "funcionarios/{funcionarios_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int funcionarios_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
    }
  }

  response = null
  guid = "2Avyataa5_gqh5nBlh8BQbBcUJE"
}