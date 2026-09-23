// Get ordens_servico record
query "ordens_servico/{ordens_servico_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int ordens_servico_id? filters=min:1
  }

  stack {
    db.get ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "VHi9aYRau7iZIUwKirqWkA4z2xg"
}