// Edit motos_clientes record
query "motos_clientes/{motos_clientes_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int motos_clientes_id? filters=min:1
    dblink {
      table = "motos_clientes"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch motos_clientes {
      field_name = "id"
      field_value = $input.motos_clientes_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "HtMusiClhmZPnUnv7zBlp17sSy4"
}