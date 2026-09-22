// Query all tokens records
query tokens verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query tokens {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "oUJ1wvQTRgt33RpenFYSNvOrzGc"
}