// Add CEP record
query cep verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "CEP"
    }
  }

  stack {
    db.add CEP {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $cep
  }

  response = $cep
  guid = "qGThlXfsHYeRZG29jTFtMpu5xyo"
}