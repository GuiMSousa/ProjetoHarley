// Query all transacoes records
query transacoes verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query transacoes {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "VIaFQU_ReCZvJFE2rxkooYcCYNE"
}