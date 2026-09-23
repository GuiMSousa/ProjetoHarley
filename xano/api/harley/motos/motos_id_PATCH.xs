// Edit motos record
query "motos/{motos_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int motos_id? filters=min:1
    dblink {
      table = "motos"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch motos {
      field_name = "id"
      field_value = $input.motos_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $motos
  }

  response = $motos
  guid = "co0x9ziQKCBPsWAPpmov6mtCp_g"
}