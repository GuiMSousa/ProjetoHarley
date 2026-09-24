// Get clientes record
query "clientes/{clientes_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int clientes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.get clientes {
      field_name = "id"
      field_value = $input.clientes_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "IKpFVZmzkQGT20wMAgk91RCZt_k"
}