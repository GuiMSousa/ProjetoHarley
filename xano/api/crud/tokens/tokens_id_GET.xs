// Get tokens record
query "tokens/{tokens_id}" verb=GET {
  api_group = "Crud"

  input {
    int tokens_id? filters=min:1
  }

  stack {
    db.get tokens {
      field_name = "id"
      field_value = $input.tokens_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "LEio_Qpxl3SdqB-lHxZNEfT5dfY"
}