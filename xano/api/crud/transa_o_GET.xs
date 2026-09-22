// Query all TRANSAÇÃO records
query transa_o verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query "TRANSAÇÃO" {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "2Uz8UQtNOXKaO99d5KtICSLBits"
}