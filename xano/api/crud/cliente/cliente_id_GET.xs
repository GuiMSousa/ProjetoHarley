// Get CLIENTE record
query "cliente/{cliente_id}" verb=GET {
  api_group = "Crud"

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
  guid = "3VfKYMx-p7duHNqhyhZ6ksUJHsA"
}