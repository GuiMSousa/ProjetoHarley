// Query all OE records
query oe verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query OE {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "3FW6MCbmHfS_pJlOKD3coX4NeNA"
}