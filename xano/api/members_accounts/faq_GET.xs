// Query all FAQ records
query faq verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query FAQ {
      return = {type: "list"}
    } as $faq
  }

  response = $faq
  guid = "nIWU2I96lgLyp4rFl6BYzhuOEKM"
}