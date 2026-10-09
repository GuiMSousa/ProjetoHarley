// Bloqueado na Change 10 (D5): transações são imutáveis; correções serão feitas por estorno.
query "transacoes/{transacoes_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int transacoes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Transações são imutáveis."
    }
  }

  response = null
  guid = "lrIAO8FMCZxGAIaNQqpTi0eVq9k"
}
