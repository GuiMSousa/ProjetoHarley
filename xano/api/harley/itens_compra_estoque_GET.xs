// Query all itens_compra_estoque records
query itens_compra_estoque verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query itens_compra_estoque {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "w1JaaKcSQb64ntjWH73OgsBUZIk"
}