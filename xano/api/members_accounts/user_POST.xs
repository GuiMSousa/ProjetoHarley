// Add USER record
query user verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "USER"
    }
  }

  stack {
    db.add USER {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $user
  }

  response = $user
  guid = "_phTpbVOxiJijZ0aC8qhNL6rdy8"
}