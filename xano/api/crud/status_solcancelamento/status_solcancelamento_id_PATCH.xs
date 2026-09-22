// Edit STATUS_SOLCANCELAMENTO record
query "status_solcancelamento/{status_solcancelamento_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int status_solcancelamento_id? filters=min:1
    dblink {
      table = "STATUS_SOLCANCELAMENTO"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.status_solcancelamento_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "6icR8l0PsqvsV-QnA6O6rH26Q2o"
}