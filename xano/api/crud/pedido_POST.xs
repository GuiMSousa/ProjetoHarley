// Add PEDIDO record
query pedido verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "PEDIDO"
    }
  }

  stack {
    db.add PEDIDO {
      enforce_hidden_fields = false
      data = {
        created_at      : "now"
        total           : $input.total
        nfc_e           : $input.nfc_e
        cod_entrega     : $input.cod_entrega
        cliente_id      : $input.cliente_id
        status_pedido_id: $input.status_pedido_id
      }
    } as $model
  }

  response = $model
  guid = "FDltnRhnCDrIrov3wESHe6rcHUk"
}