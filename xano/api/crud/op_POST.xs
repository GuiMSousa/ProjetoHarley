// Add OP record
query op verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "OP"
    }
  }

  stack {
    db.add OP {
      enforce_hidden_fields = false
      data = {
        created_at  : "now"
        pedido_id   : $input.pedido_id
        status_op_id: $input.status_op_id
      }
    } as $model
  }

  response = $model
  guid = "sZ4MH4OZqR8G8EpY4x8iIHsn7-A"
}