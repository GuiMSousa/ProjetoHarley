// Query all TESTORNO records
query testorno verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query TESTORNO {
      return = {type: "list"}
    } as $testorno
  }

  response = $testorno
  guid = "zHPzODRpO2OjyggqhxNRaWp4HS4"
}