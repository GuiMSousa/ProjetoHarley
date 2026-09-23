// Query all motos records
query motos verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query motos {
      return = {type: "list"}
    } as $motos
  }

  response = $motos
  guid = "MmiokOmzzZysN1u43xASFIsdQm0"
}