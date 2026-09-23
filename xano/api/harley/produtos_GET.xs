// Query all produtos records
query produtos verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query produtos {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ZAIunWDZBYm38BNIOZ3h5SPQeeo"
}