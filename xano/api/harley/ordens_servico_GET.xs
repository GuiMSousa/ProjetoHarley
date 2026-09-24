// Query all ordens_servico records
query ordens_servico verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query ordens_servico {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ejDbmcP8h6RVydMZ06OpqGhtIO0"
}