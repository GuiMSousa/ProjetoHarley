// Edit fornecedores record
query "fornecedores/{fornecedores_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int fornecedores_id? filters=min:1
    dblink {
      table = "fornecedores"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch fornecedores {
      field_name = "id"
      field_value = $input.fornecedores_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "uAjYL5Jp9m1hfzqmunqjbmr4pwQ"
}