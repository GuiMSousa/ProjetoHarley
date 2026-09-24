// Query all motos_clientes records
query motos_clientes verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query motos_clientes {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "WRKFpHDVYQstjDXZENSPmYRFrco"
}