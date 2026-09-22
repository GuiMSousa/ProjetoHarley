// Query all STATUS_OP records
query status_op verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_OP {
      return = {type: "list"}
    } as $status_op
  }

  response = $status_op
  guid = "mfKnir6DOfH8xUT4PuO0dPJvT78"
}