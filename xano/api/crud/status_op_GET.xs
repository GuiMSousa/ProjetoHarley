// Query all STATUS_OP records
query status_op verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_OP {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "687TAKST8Ay6fdhkd9iY-3HLLr8"
}