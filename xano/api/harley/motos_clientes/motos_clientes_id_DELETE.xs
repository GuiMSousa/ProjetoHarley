// Delete motos_clientes record
query "motos_clientes/{motos_clientes_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_clientes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del motos_clientes {
      field_name = "id"
      field_value = $input.motos_clientes_id
    }
  }

  response = null
  guid = "Xy2VcUX_g6UC3i_SGAEsIHk2TJQ"
}