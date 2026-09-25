// Bloqueado na Change 6: OS mudam somente por abertura e transição de status;
// itens de OS aguardam a Change de itens com baixa de estoque.
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
      error = "Itens de OS estarão disponíveis na etapa de itens com baixa de estoque."
    }
  }

  response = null
  guid = "9kUTmzonk0E3SjsPRJL3rrjL84Q"
}
