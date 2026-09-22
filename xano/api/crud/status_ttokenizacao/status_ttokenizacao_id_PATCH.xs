// Edit STATUS_TTOKENIZACAO record
query "status_ttokenizacao/{status_ttokenizacao_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int status_ttokenizacao_id? filters=min:1
    dblink {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_TTOKENIZACAO {
      field_name = "id"
      field_value = $input.status_ttokenizacao_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "Rp5_gRBQqAEJwSQE-ejiQmkEP9A"
}