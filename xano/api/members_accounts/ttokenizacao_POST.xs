// Add TTOKENIZACAO record
query ttokenizacao verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "TTOKENIZACAO"
    }
  }

  stack {
    db.add TTOKENIZACAO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $ttokenizacao
  }

  response = $ttokenizacao
  guid = "-LVvB_R1I2eR6_fjLKPbvzy1SUs"
}