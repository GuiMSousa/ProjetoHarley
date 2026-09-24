// Query all entrada_mercadoria records
query entrada_mercadoria verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      db.query entrada_mercadoria {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "TfNTbEqZ2VB_fjEZK9XJlNQtdKo"
}