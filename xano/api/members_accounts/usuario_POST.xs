// Add Usuario record
query usuario verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = ""
    }
  }

  stack {
    db.add "" {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $usuario
  }

  response = $usuario
  guid = "eSUArBe1eDPC0AOFaJfhg2JZfRc"
}