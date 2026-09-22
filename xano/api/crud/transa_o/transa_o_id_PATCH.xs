// Edit TRANSAÇÃO record
query "transa_o/{transa_o_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int transa_o_id? filters=min:1
    dblink {
      table = "TRANSAÇÃO"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch "TRANSAÇÃO" {
      field_name = "id"
      field_value = $input.transa_o_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "EajErlXGEV14vG5gfOd5MCa06iQ"
}