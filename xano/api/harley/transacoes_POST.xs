// Bloqueado na Change 10 (D5): transações nascem somente das operações de negócio (venda de moto
// e conclusão de OS) e são imutáveis. Correções serão feitas por estorno numa Change futura.
query transacoes verb=POST {
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
      error = "Transações são registradas somente pelas operações de venda e de oficina."
    }
  }

  response = null
  guid = "0rGHlasmcKmdcQD9cpHBeWBCoZI"
}
