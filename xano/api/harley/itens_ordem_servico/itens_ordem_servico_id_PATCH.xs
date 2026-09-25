// Bloqueado: itens de OS mudam somente por POST/DELETE ordens_servico/{id}/itens,
// que aplicam a baixa e a devolução de estoque (Change 7).
query "itens_ordem_servico/{itens_ordem_servico_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int itens_ordem_servico_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Use POST/DELETE ordens_servico/{id}/itens."
    }
  }

  response = null
  guid = "gJJEEwg4eczxw7EVVyHk4_us0cI"
}
