// Get TTOKENIZACAO record
query "ttokenizacao/{ttokenizacao_id}" verb=GET {
  api_group = "Crud"

  input {
    int ttokenizacao_id? filters=min:1
  }

  stack {
    db.get TTOKENIZACAO {
      field_name = "id"
      field_value = $input.ttokenizacao_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "9aS2Ndr4JZuMTjZnBBIwq1PKo2o"
}