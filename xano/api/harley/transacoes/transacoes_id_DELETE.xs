// Delete transacoes record
query "transacoes/{transacoes_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int transacoes_id? filters=min:1
  }

  stack {
    db.del transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
    }
  }

  response = null
  guid = "yosDdJa-wLdEMYT3kfJyXNgb0EA"
}