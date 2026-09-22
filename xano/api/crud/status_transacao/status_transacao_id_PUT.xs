// Update STATUS_TRANSACAO record
query "status_transacao/{status_transacao_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_transacao_id? filters=min:1
    dblink {
      table = "STATUS_TRANSACAO"
    }
  }

  stack {
    db.edit STATUS_TRANSACAO {
      field_name = "id"
      field_value = $input.status_transacao_id
      enforce_hidden_fields = false
      data = {status: $input.status}
    } as $model
  }

  response = $model
  guid = "Di8Ig8sWXSRIaT4UdVewmN2pL2A"
}