// Edit STATUS_PEDIDO record
query "status_pedido/{status_pedido_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int status_pedido_id? filters=min:1
    dblink {
      table = "STATUS_PEDIDO"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_PEDIDO {
      field_name = "id"
      field_value = $input.status_pedido_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "09kVuYkJiPDc74Ur3iuw2mICXsU"
}