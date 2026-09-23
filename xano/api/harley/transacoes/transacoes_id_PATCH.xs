// Edit transacoes record
query "transacoes/{transacoes_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int transacoes_id? filters=min:1
    dblink {
      table = "transacoes"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "lrIAO8FMCZxGAIaNQqpTi0eVq9k"
}