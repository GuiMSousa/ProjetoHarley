// Bloqueado: itens de OS mudam somente por POST/DELETE ordens_servico/{id}/itens,
// que aplicam a baixa e a devolução de estoque (Change 7).
query itens_ordem_servico verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
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
  guid = "9kUTmzonk0E3SjsPRJL3rrjL84Q"
}
