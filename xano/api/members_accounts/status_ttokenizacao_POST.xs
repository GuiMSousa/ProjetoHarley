// Add STATUS_TTOKENIZACAO record
query status_ttokenizacao verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  stack {
    db.add STATUS_TTOKENIZACAO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $status_ttokenizacao
  }

  response = $status_ttokenizacao
  guid = "Nb2XfKdaF2T8C4gXMy4TOSoMzik"
}