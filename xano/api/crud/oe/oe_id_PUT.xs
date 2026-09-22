// Update OE record
query "oe/{oe_id}" verb=PUT {
  api_group = "Crud"

  input {
    int oe_id? filters=min:1
    dblink {
      table = "OE"
    }
  }

  stack {
    db.edit OE {
      field_name = "id"
      field_value = $input.oe_id
      enforce_hidden_fields = false
      data = {
        pedido_id   : $input.pedido_id
        status_oe_id: $input.status_oe_id
      }
    } as $model
  }

  response = $model
  guid = "YHK4pMs6taJBylOqUm6fQw_p-Cw"
}