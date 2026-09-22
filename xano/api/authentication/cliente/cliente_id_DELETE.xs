// Delete CLIENTE record
query "cliente/{cliente_id}" verb=DELETE {
  api_group = "Authentication"

  input {
    int cliente_id? filters=min:1
  }

  stack {
    db.del CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
    }
  }

  response = null
  guid = "tGOa3Vj98vRsYSvsTlipJn5mCyE"
}