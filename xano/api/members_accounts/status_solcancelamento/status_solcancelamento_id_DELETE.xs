// Delete STATUS_SOLCANCELAMENTO record.
query "status_solcancelamento/{status_solcancelamento_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int status_solcancelamento_id? filters=min:1
  }

  stack {
    db.del STATUS_SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.status_solcancelamento_id
    }
  }

  response = null
  guid = "uIqXcWPtgsAODM_48JxZqtUaqi0"
}