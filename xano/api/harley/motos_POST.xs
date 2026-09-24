// Add motos record
query motos verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "motos"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.add motos {
      enforce_hidden_fields = false
      data = {
        clientes_id: $input.clientes_id
        marca      : $input.marca
        modelo     : $input.modelo
        created_at : "now"
      }
    } as $motos
  }

  response = $motos
  guid = "S_vB5rNqdGX96LtJUuzpJ_J3038"
}