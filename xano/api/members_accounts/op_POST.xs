// Add OP record
query op verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "OP"
    }
  }

  stack {
    db.add OP {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $op
  }

  response = $op
  guid = "J8UoC-hWCzT5D221nOEJZIdIYsI"
}