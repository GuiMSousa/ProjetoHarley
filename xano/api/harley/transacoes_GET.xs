// Lista as transações financeiras. Dados financeiros: somente GERENTE (saneamento pós-Change 9).
query transacoes verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.query transacoes {
      sort = {data_transacao: "desc"}
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "VIaFQU_ReCZvJFE2rxkooYcCYNE"
}
