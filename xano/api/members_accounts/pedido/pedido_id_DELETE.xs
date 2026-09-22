// Delete PEDIDO record.
query "pedido/{pedido_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int pedido_id? filters=min:1
  }

  stack {
    db.del PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
    }
  }

  response = null
  guid = "RQwc_5AHMLbh1ppIlR0FnF4zZD8"
}