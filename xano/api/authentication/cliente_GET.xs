// Query all CLIENTE records
query cliente verb=GET {
  api_group = "Authentication"

  input {
  }

  stack {
    db.query CLIENTE {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "dlpEUeUEAYWfR_7M0TybNFu-iqE"
}