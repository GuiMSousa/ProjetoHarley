// Delete STATUS_TRANSACAO record.
query "status_transacao/{status_transacao_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int status_transacao_id? filters=min:1
  }

  stack {
    db.del "" {
      field_name = "id"
      field_value = $input.status_transacao_id
    }
  }

  response = null
  guid = "gXZt7hGswIRfT_rHTmmK4IFNMqE"
}