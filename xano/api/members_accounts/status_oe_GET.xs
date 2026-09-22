// Query all STATUS_OE records
query status_oe verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_OE {
      return = {type: "list"}
    } as $status_oe
  }

  response = $status_oe
  guid = "Cw2CXqs1vl5KOnm5HhYOZRhU3iw"
}