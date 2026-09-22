// Update STATUS_PEDIDO record
query "status_pedido/{status_pedido_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_pedido_id? filters=min:1
    dblink {
      table = "STATUS_PEDIDO"
    }
  }

  stack {
    db.edit STATUS_PEDIDO {
      field_name = "id"
      field_value = $input.status_pedido_id
      enforce_hidden_fields = false
      data = {status: $input.status, status_para: $input.status_para}
    } as $model
  }

  response = $model
  guid = "FwHdX34HCIxsF3asVnPdEnI-k-4"
}