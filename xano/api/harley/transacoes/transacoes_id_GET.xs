// Get transacoes record
query "transacoes/{transacoes_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int transacoes_id? filters=min:1
  }

  stack {
    db.get transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "nV4Q8tyedV9DpHx1US8cAIvcar4"
}