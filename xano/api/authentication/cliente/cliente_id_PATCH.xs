// Edit CLIENTE record
query "cliente/{cliente_id}" verb=PATCH {
  api_group = "Authentication"

  input {
    int cliente_id? filters=min:1
    dblink {
      table = "CLIENTE"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "uFg-ESngo0Pvs8BVRKqvPyBiVQw"
}