// Edit TRANSAÇÃO record
query "transa_o/{transa_o_id}" verb=PATCH {
  api_group = "Members & Accounts"

  input {
    int transa_o_id? filters=min:1
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
      field_value = $input.transa_o_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $transa_o
  }

  response = $transa_o
  guid = "7Rjlx5lT0oL0JR5rowvBm82wQhc"
}