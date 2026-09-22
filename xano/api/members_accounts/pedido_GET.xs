// Query all PEDIDO records
query pedido verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query PEDIDO {
      return = {type: "list"}
    } as $pedido
  }

  response = $pedido
  guid = "5dvajLrDNdoYktca_3HBH8uyoDA"
}