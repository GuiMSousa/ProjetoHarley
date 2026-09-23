// Delete clientes record
query "clientes/{clientes_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int clientes_id? filters=min:1
  }

  stack {
    db.del clientes {
      field_name = "id"
      field_value = $input.clientes_id
    }
  }

  response = null
  guid = "kuyr19XZtxy7sZQgQGQxFwNlKFM"
}