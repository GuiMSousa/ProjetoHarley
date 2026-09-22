// Update STATUS_SOLCANCELAMENTO record
query "status_solcancelamento/{status_solcancelamento_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_solcancelamento_id? filters=min:1
    dblink {
      table = "STATUS_SOLCANCELAMENTO"
    }
  }

  stack {
    db.edit STATUS_SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.status_solcancelamento_id
      enforce_hidden_fields = false
      data = {status: $input.status}
    } as $model
  }

  response = $model
  guid = "vafVP9XBqj9JqqlaGDpvG_ngYGY"
}