// Query all entrada_mercadoria records
query entrada_mercadoria verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query entrada_mercadoria {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "TfNTbEqZ2VB_fjEZK9XJlNQtdKo"
}