// Bloqueado no saneamento pós-Change 7: exclusão física desabilitada para que registros
// vinculados a OS, estoque, entradas e transações nunca fiquem órfãos.
query "transacoes/{transacoes_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int transacoes_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Exclusão física desabilitada: o ciclo de vida das transações será definido na Change de vendas."
    }
  }

  response = null
  guid = "yosDdJa-wLdEMYT3kfJyXNgb0EA"
}
