// Update PEDIDO record
query "pedido/{pedido_id}" verb=PUT {
  api_group = "Crud"

  input {
    int pedido_id? filters=min:1
    dblink {
      table = "PEDIDO"
    }
  }

  stack {
    db.edit PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
      enforce_hidden_fields = false
      data = {
        total           : $input.total
        nfc_e           : $input.nfc_e
        cod_entrega     : $input.cod_entrega
        cliente_id      : $input.cliente_id
        status_pedido_id: $input.status_pedido_id
      }
    } as $model
  }

  response = $model
  guid = "niM0jkcSaoZWFmh2bYiGywyr-84"
}