// Add CLIENTE record
query cliente verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "CLIENTE"
    }
  }

  stack {
    db.add CLIENTE {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $cliente
  }

  response = $cliente
  guid = "d79zWqC--tA8fVLLdF6P-A8pzyI"
}