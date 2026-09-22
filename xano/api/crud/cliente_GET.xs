// Query all CLIENTE records
query cliente verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query CLIENTE {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ejR3g6JzhZwgWwPbWd9V75USGhM"
}