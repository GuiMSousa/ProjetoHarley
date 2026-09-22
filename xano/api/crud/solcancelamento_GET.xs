// Query all SOLCANCELAMENTO records
query solcancelamento verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query SOLCANCELAMENTO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "m5xtVBDXszFmbowO3We1crY-i74"
}