// Bloqueado na Change 5: a movimentação de estoque ocorre somente em POST entrada_mercadoria.
query itens_compra_estoque verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Itens de compra só podem ser registrados junto com a entrada de mercadoria."
    }
  }

  response = null
  guid = "VKz4tbuSfze4ostoFxr9mHwbvsY"
}
