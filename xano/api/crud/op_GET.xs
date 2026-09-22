// Query all OP records
query op verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query OP {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ujhEL9fH6MMxjsmpF2DbFrosX14"
}