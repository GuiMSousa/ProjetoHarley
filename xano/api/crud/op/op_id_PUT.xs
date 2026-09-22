// Update OP record
query "op/{op_id}" verb=PUT {
  api_group = "Crud"

  input {
    int op_id? filters=min:1
    dblink {
      table = "OP"
    }
  }

  stack {
    db.edit OP {
      field_name = "id"
      field_value = $input.op_id
      enforce_hidden_fields = false
      data = {
        pedido_id   : $input.pedido_id
        status_op_id: $input.status_op_id
      }
    } as $model
  }

  response = $model
  guid = "gZY2HrE-bNOczMLddXgA07X6_v8"
}