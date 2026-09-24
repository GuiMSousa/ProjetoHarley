// Query all fornecedores records
query fornecedores verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query fornecedores {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "f64_SmabpKLmfeu_4hhUJb0LkFA"
}