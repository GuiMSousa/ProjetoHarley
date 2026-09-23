// Query all motos_clientes records
query motos_clientes verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query motos_clientes {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "WRKFpHDVYQstjDXZENSPmYRFrco"
}