// Edit Usuario record
query "usuario/{usuario_id}" verb=PATCH {
  api_group = "Members & Accounts"

  input {
    int usuario_id? filters=min:1
    dblink {
      table = ""
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch "" {
      field_name = "id"
      field_value = $input.usuario_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $usuario
  }

  response = $usuario
  guid = "h1xWjJfzqORGezfkJLPtTuXnPBY"
}