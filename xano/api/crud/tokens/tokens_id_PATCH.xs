// Edit tokens record
query "tokens/{tokens_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int tokens_id? filters=min:1
    dblink {
      table = "tokens"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch tokens {
      field_name = "id"
      field_value = $input.tokens_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "e0LDNrmyqsCsiOdNHX5xrq4lW4A"
}