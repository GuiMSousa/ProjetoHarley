// Edit USER record
query "user/{user_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int user_id? filters=min:1
    dblink {
      table = "USER"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch USER {
      field_name = "id"
      field_value = $input.user_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "c1qGPIax0n-GEm1z9JV8g_cMpv4"
}