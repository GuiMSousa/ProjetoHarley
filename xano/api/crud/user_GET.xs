// Query all USER records
query user verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query USER {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "dg8o5xYsJXRqeWRdmibBU2bTP7I"
}