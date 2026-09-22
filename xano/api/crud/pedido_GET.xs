// Query all PEDIDO records
query pedido verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query PEDIDO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "3k_hfwuPwRlpM4Tv6CgB-11gPsE"
}