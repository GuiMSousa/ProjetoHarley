// Add STATUS_TESTORNO record
query status_testorno verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_TESTORNO"
    }
  }

  stack {
    db.add STATUS_TESTORNO {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "xITs52xTc7iAaa7DuYoMCX0U31Q"
}