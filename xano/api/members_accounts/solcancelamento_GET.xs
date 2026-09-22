// Query all SOLCANCELAMENTO records
query solcancelamento verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query SOLCANCELAMENTO {
      return = {type: "list"}
    } as $solcancelamento
  }

  response = $solcancelamento
  guid = "MTU1-MC6ufulI-ERPTbUHZpubCY"
}