// Delete OE record
query "oe/{oe_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int oe_id? filters=min:1
  }

  stack {
    db.del OE {
      field_name = "id"
      field_value = $input.oe_id
    }
  }

  response = null
  guid = "zWs79HnH12Meu6XWQpV-9b1XKzg"
}