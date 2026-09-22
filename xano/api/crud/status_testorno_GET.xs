// Query all STATUS_TESTORNO records
query status_testorno verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_TESTORNO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "4vLmTG-ciFkI4mP12dhYMbxh0Xw"
}