// Query all OP records
query op verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query OP {
      return = {type: "list"}
    } as $op
  }

  response = $op
  guid = "i3jPToW1jbPv9d_PAZUzFH6lrS8"
}