// Query all USER records
query user verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query USER {
      return = {type: "list"}
    } as $user
  }

  response = $user
  guid = "lxR5-wQiP1aywQTj49qLFriDXJM"
}