// Get PRODUTO record
query "produto/{produto_id}" verb=GET {
  api_group = "Crud"

  input {
    int produto_id? filters=min:1
  }

  stack {
    db.get PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "wZn6IeuYamQG-knQ2ukDgbAituY"
}