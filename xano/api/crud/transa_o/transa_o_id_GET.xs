// Get TRANSAÇÃO record
query "transa_o/{transa_o_id}" verb=GET {
  api_group = "Crud"

  input {
    int transa_o_id? filters=min:1
  }

  stack {
    db.get "TRANSAÇÃO" {
      field_name = "id"
      field_value = $input.transa_o_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "qjjeWEINCk6rI1x_guZKGf2OTpY"
}