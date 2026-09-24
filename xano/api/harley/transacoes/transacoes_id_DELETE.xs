// Delete transacoes record
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
      db.del transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
    }
  }

  response = null
  guid = "yosDdJa-wLdEMYT3kfJyXNgb0EA"
}