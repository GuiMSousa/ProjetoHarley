// Get entrada_mercadoria record with its items
query "entrada_mercadoria/{entrada_mercadoria_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int entrada_mercadoria_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check

    function.run "Estoque/detalhe_entrada" {
      input = {entrada_id: $input.entrada_mercadoria_id}
    } as $model
  }

  response = $model
  guid = "K_3T6zhmIleV3VOmFVI9__X0OsU"
}
