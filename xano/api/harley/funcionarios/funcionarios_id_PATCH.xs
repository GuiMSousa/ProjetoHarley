// Edit funcionarios record
query "funcionarios/{funcionarios_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int funcionarios_id? filters=min:1
    dblink {
      table = "funcionarios"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "-LRpgIR7T4mdtcEco34Hq4AYn7E"
}