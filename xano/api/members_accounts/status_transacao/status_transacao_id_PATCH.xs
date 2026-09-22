// Edit STATUS_TRANSACAO record
query "status_transacao/{status_transacao_id}" verb=PATCH {
  api_group = "Members & Accounts"

  input {
    int status_transacao_id? filters=min:1
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
      field_value = $input.status_transacao_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_transacao
  }

  response = $status_transacao
  guid = "raljDIIxM-lFlPYAlIjtteNKYuI"
}