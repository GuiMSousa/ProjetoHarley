// Get STATUS_TESTORNO record
query "status_testorno/{status_testorno_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int status_testorno_id? filters=min:1
  }

  stack {
    db.get STATUS_TESTORNO {
      field_name = "id"
      field_value = $input.status_testorno_id
    } as $status_testorno
  
    precondition ($status_testorno != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $status_testorno
  guid = "meNWEo4jylsA7y09_3HUgGNvOig"
}