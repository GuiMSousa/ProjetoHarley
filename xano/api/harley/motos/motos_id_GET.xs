// Detalhe interno de uma unidade do estoque com a linha do tempo de status (Change 8).
query "motos/{motos_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check

    function.run "Vendas/detalhe_moto" {
      input = {moto_id: $input.motos_id}
    } as $detalhe
  }

  response = $detalhe
  guid = "WTwEoKXXeg7Gftj_J5gR4eaKw98"
}
