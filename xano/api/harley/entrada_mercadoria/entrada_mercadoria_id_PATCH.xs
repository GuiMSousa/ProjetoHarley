// Bloqueado na Change 5: a movimentação de estoque ocorre somente em POST entrada_mercadoria.
query "entrada_mercadoria/{entrada_mercadoria_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int entrada_mercadoria_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Entradas de mercadoria são imutáveis. Registre uma nova entrada."
    }
  }

  response = null
  guid = "KjyhKgxJ76vNW-DYnWCa_te6N3U"
}
