// Update STATUS_TESTORNO record
query "status_testorno/{status_testorno_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_testorno_id? filters=min:1
    dblink {
      table = "STATUS_TESTORNO"
    }
  }

  stack {
    db.edit STATUS_TESTORNO {
      field_name = "id"
      field_value = $input.status_testorno_id
      enforce_hidden_fields = false
      data = {status: $input.status}
    } as $model
  }

  response = $model
  guid = "cTmF1s_jdAdJQSnL73m6YHe3hiE"
}