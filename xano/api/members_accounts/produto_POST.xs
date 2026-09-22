// Add PRODUTO record
query produto verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "PRODUTO"
    }
  }

  stack {
    db.add PRODUTO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $produto
  }

  response = $produto
  guid = "i3pIPvMLvp3PVrjls3lXfkTyVS0"
}