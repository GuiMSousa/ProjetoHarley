// Edit transacoes record. A autoria (id_funcionario) é definida na criação e nunca é aceita do payload.
query "transacoes/{transacoes_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int transacoes_id? filters=min:1
    dblink {
      table = "transacoes"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
      data = `$input|pick:($raw_input|keys)`|unset:"id_funcionario"|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "lrIAO8FMCZxGAIaNQqpTi0eVq9k"
}