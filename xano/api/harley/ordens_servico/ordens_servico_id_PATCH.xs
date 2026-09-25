// Bloqueado na Change 6: OS mudam somente por abertura e transição de status;
// itens de OS aguardam a Change de itens com baixa de estoque.
query "ordens_servico/{ordens_servico_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Ordens de serviço não são editadas nem excluídas diretamente. Use a transição de status."
    }
  }

  response = null
  guid = "qrJqBvJ__Wjj9OTY9f_lMMoBrRI"
}
