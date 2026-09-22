// Add OE record
query oe verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "OE"
    }
  }

  stack {
    db.add OE {
      enforce_hidden_fields = false
      data = {
        created_at  : "now"
        pedido_id   : $input.pedido_id
        status_oe_id: $input.status_oe_id
      }
    } as $model
  }

  response = $model
  guid = "fRLP-9tFP-O1lzXC591vBr76bzo"
}