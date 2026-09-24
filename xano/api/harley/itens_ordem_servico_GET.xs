// Query all itens_ordem_servico records
query itens_ordem_servico verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query itens_ordem_servico {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "6L-m1ZhwAv8DmPKnuKE8Lz4zVKk"
}