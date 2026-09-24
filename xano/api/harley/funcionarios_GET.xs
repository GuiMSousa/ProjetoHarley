// Query all funcionarios records
query funcionarios verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.query funcionarios {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "h70LjpnyCsc0Vof6gUfLN3jOGjc"
}