// Query all STATUS_TESTORNO records
query status_testorno verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_TESTORNO {
      return = {type: "list"}
    } as $status_testorno
  }

  response = $status_testorno
  guid = "kkKetpAcVIlNDefT5mobgb1hWg8"
}