// Add STATUS_TRANSACAO record
query status_transacao verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = ""
    }
  }

  stack {
    db.add "" {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $status_transacao
  }

  response = $status_transacao
  guid = "geUDqxzoEGNvYtpvfZB-xBE_iy4"
}