table itens_compra_estoque {
  auth = false

  schema {
    int id
    int id_entrada {
      table = "entrada_mercadoria"
    }
  
    int id_produto {
      table = "produtos"
    }
  
    int quantidade filters=min:1
    decimal valor_unitario filters=min:0
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_entrada"}]}
    {type: "btree", field: [{name: "id_produto"}]}
  ]

  guid = "jsMsKgGFpDP2mv8PQl3xygWuc3U"
}