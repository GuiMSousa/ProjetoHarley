// Get funcionarios record
query "funcionarios/{funcionarios_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int funcionarios_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.get funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "TFxl03nMwHm2ySjDvkKAetUafNQ"
}