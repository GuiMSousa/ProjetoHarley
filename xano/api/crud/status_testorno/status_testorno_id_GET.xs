// Get STATUS_TESTORNO record
query "status_testorno/{status_testorno_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_testorno_id? filters=min:1
  }

  stack {
    db.get STATUS_TESTORNO {
      field_name = "id"
      field_value = $input.status_testorno_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "g4JvoJ15kXpBl8fzyIFjYPyPbcg"
}