// Bloqueado na Change 6: OS mudam somente por abertura e transição de status;
// itens de OS aguardam a Change de itens com baixa de estoque.
query "itens_ordem_servico/{itens_ordem_servico_id}" verb=DELETE {
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
      error = "Itens de OS estarão disponíveis na etapa de itens com baixa de estoque."
    }
  }

  response = null
  guid = "RuZEyes7dJzSaYzFlX3c-Nj_p8s"
}
