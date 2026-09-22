// Query all STATUS_PEDIDO records
query status_pedido verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_PEDIDO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "paepaGYRB_ueL0IYpq9TmUeNYv8"
}