// Query all CEP records
query cep verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query CEP {
      return = {type: "list"}
    } as $cep
  }

  response = $cep
  guid = "pHvIibC3RQ2Ix7Ubl_juoIdmQaM"
}