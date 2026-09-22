// Add SOLCANCELAMENTO record
query solcancelamento verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "SOLCANCELAMENTO"
    }
  }

  stack {
    db.add SOLCANCELAMENTO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $solcancelamento
  }

  response = $solcancelamento
  guid = "nOvMrmDyGzHx3sUiLyFoDxthWTk"
}