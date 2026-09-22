// Query all STATUS_PEDIDO records
query status_pedido verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_PEDIDO {
      return = {type: "list"}
    } as $status_pedido
  }

  response = $status_pedido
  guid = "B8ewcmtr2CRT15mNe0DzYEyFm88"
}