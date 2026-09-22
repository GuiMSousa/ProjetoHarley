// Query all TESTORNO records
query testorno verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query TESTORNO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "wcC7nbRZAVz7dzIqmeIaLeV5GGE"
}