// Query all itens_compra_estoque records
query itens_compra_estoque verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      db.query itens_compra_estoque {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "w1JaaKcSQb64ntjWH73OgsBUZIk"
}