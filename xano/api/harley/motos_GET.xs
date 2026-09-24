// Query all motos records
query motos verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query motos {
      return = {type: "list"}
    } as $motos
  }

  response = $motos
  guid = "MmiokOmzzZysN1u43xASFIsdQm0"
}