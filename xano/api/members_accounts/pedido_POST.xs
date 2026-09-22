// Add PEDIDO record
query pedido verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "PEDIDO"
    }
  }

  stack {
    db.add PEDIDO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $pedido
  }

  response = $pedido
  guid = "KpmKVraQBVJhgCfm5A_xOMdrRAU"
}