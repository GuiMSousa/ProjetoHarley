// Update motos record
query "motos/{motos_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id? filters=min:1
    dblink {
      table = "motos"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.edit motos {
      field_name = "id"
      field_value = $input.motos_id
      enforce_hidden_fields = false
      data = {
        clientes_id: $input.clientes_id
        marca      : $input.marca
        modelo     : $input.modelo
      }
    } as $model
  }

  response = $model
  guid = "2aio88YHrIlhJQycs4iQjoyRqUc"
}