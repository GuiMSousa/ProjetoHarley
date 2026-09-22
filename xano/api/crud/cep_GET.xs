// Query all CEP records
query cep verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query CEP {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "5pKINj-tLEDZ_XyZLBfoUDdNtkM"
}