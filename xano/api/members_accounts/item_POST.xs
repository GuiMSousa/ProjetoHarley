// Add ITEM record
query item verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "ITEM"
    }
  }

  stack {
    db.add ITEM {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $item
  }

  response = $item
  guid = "asGnwEAbmyahEpfFJQ37Bw6tYjU"
}