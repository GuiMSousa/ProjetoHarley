// Get STATUS_SOLCANCELAMENTO record
query "status_solcancelamento/{status_solcancelamento_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_solcancelamento_id? filters=min:1
  }

  stack {
    db.get STATUS_SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.status_solcancelamento_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "7SOf0r4KxKlTrUvvq_w04nhFosM"
}