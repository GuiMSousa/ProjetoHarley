// Bloqueado na Change 5: a movimentação de estoque ocorre somente em POST entrada_mercadoria.
query "itens_compra_estoque/{itens_compra_estoque_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int itens_compra_estoque_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Itens de compra são imutáveis após o registro da entrada."
    }
  }

  response = null
  guid = "2rUQ8VGLnloVmv6gUejIRT13nBs"
}
