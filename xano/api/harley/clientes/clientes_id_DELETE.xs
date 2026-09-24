// Delete clientes record
query "clientes/{clientes_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int clientes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del clientes {
      field_name = "id"
      field_value = $input.clientes_id
    }
  }

  response = null
  guid = "kuyr19XZtxy7sZQgQGQxFwNlKFM"
}