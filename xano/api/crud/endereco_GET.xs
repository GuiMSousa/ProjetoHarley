// Query all ENDERECO records
query endereco verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query ENDERECO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "GATNQsQMXKlEgrCglknnTgZrpyo"
}