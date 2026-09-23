// Add motos record
query motos verb=POST {
  api_group = "HARLEY"

  input {
    dblink {
      table = "motos"
    }
  }

  stack {
    db.add motos {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $motos
  }

  response = $motos
  guid = "S_vB5rNqdGX96LtJUuzpJ_J3038"
}