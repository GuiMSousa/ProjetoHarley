// Query all STATUS_TRANSACAO records
query status_transacao verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_TRANSACAO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "t3-E9N6yyZgnsN1hipo3WEHN8JI"
}