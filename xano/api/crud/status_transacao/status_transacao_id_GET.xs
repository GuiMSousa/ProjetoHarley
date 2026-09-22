// Get STATUS_TRANSACAO record
query "status_transacao/{status_transacao_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_transacao_id? filters=min:1
  }

  stack {
    db.get STATUS_TRANSACAO {
      field_name = "id"
      field_value = $input.status_transacao_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "qm25VidksRTwgwk_JUg-LGBb09w"
}