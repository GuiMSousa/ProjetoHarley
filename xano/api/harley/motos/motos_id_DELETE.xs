// Delete motos record.
query "motos/{motos_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del motos {
      field_name = "id"
      field_value = $input.motos_id
    }
  }

  response = null
  guid = "dumK3HpzH_-yybpBC0jVpMEHdUo"
}