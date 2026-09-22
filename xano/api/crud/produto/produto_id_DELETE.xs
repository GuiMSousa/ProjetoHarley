// Delete PRODUTO record
query "produto/{produto_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int produto_id? filters=min:1
  }

  stack {
    db.del PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    }
  }

  response = null
  guid = "ydUdcQoX67bl0vgWcgErUBUDsYE"
}