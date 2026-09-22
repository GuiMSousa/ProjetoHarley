table "entrada_mercadoria" {
  auth = false

  schema {
    int id
    int id_fornecedor {
      table = "fornecedores"
    }
    timestamp data_entrada?=now
    decimal valor_total?=0 filters=min:0
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_fornecedor"}]}
  ]
  guid = "zts5RZt-pASg8DBNR3j8d8dSJ0Y"
}