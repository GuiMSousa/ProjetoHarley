// Add STATUS_PEDIDO record
query status_pedido verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "STATUS_PEDIDO"
    }
  }

  stack {
    db.add STATUS_PEDIDO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $status_pedido
  }

  response = $status_pedido
  guid = "FWYmQ348H3qyIwOFhw0pw2H0WJU"
}