// Add TESTORNO record
query testorno verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "TESTORNO"
    }
  }

  stack {
    db.add TESTORNO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $testorno
  }

  response = $testorno
  guid = "mHMT28wNrGwxyjjyC4RuA5zW5r0"
}