// Query all STATUS_TRANSACAO records
query status_transacao verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query "" {
      return = {type: "list"}
    } as $status_transacao
  }

  response = $status_transacao
  guid = "xxBct3ZK3W-gNXLkslLS0lonvys"
}