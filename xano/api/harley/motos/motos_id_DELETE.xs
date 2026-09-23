// Delete motos record.
query "motos/{motos_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int motos_id? filters=min:1
  }

  stack {
    db.del motos {
      field_name = "id"
      field_value = $input.motos_id
    }
  }

  response = null
  guid = "dumK3HpzH_-yybpBC0jVpMEHdUo"
}