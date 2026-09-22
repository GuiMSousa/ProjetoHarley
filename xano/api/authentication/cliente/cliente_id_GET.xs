// Get CLIENTE record
query "cliente/{cliente_id}" verb=GET {
  api_group = "Authentication"

  input {
    int cliente_id? filters=min:1
  }

  stack {
    db.get CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "DqviDg0OI3YffBHACWsoZW1kYsc"
}