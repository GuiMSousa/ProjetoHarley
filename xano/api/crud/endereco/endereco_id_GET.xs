// Get ENDERECO record
query "endereco/{endereco_id}" verb=GET {
  api_group = "Crud"

  input {
    int endereco_id? filters=min:1
  }

  stack {
    db.get ENDERECO {
      field_name = "id"
      field_value = $input.endereco_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "0J0TYFfWyTQtxeS-_0VQce9N0bU"
}