// Get CEP record
query "cep/{cep_id}" verb=GET {
  api_group = "Crud"

  input {
    int cep_id? filters=min:1
  }

  stack {
    db.get CEP {
      field_name = "id"
      field_value = $input.cep_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "1oGrRVqVWaebFDISzA5zK6UcYJw"
}