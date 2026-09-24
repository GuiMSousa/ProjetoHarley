// Get motos_clientes record
query "motos_clientes/{motos_clientes_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_clientes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.get motos_clientes {
      field_name = "id"
      field_value = $input.motos_clientes_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "oYOE3RxKT-T2tAuR7l2SvxIuO4k"
}