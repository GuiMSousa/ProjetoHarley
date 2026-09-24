// Delete ordens_servico record
query "ordens_servico/{ordens_servico_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
    }
  }

  response = null
  guid = "Mdvb9ON58IIY42WCRcwUeRZoY-U"
}