// Get STATUS_TTOKENIZACAO record
query "status_ttokenizacao/{status_ttokenizacao_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_ttokenizacao_id? filters=min:1
  }

  stack {
    db.get STATUS_TTOKENIZACAO {
      field_name = "id"
      field_value = $input.status_ttokenizacao_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "jh5CeSLSLVlUVE_GfvTSwXGcwxY"
}