// Delete entrada_mercadoria record
query "entrada_mercadoria/{entrada_mercadoria_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int entrada_mercadoria_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del entrada_mercadoria {
      field_name = "id"
      field_value = $input.entrada_mercadoria_id
    }
  }

  response = null
  guid = "7l8UTQ07TozPeWWcPpKngS705Gw"
}