// Add PAPEL record
query papel verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "PAPEL"
    }
  }

  stack {
    db.add PAPEL {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $papel
  }

  response = $papel
  guid = "fQWGvwtvIh1i3qPU5rzkevNNcj4"
}