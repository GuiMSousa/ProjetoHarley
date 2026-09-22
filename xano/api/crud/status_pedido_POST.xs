// Add STATUS_PEDIDO record
query status_pedido verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_PEDIDO"
    }
  }

  stack {
    db.add STATUS_PEDIDO {
      enforce_hidden_fields = false
      data = {
        created_at : "now"
        status     : $input.status
        status_para: $input.status_para
      }
    } as $model
  }

  response = $model
  guid = "nntWG_plB_R1KeKzpn-zuyfwcP0"
}