// Add STATUS_TRANSACAO record
query status_transacao verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_TRANSACAO"
    }
  }

  stack {
    db.add STATUS_TRANSACAO {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "gZ-JB2qdSIoKTSd3msmNK4b1IiU"
}