// Query all CARTAOTOKNZD records
query cartaotoknzd verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query CARTAOTOKNZD {
      return = {type: "list"}
    } as $cartaotoknzd
  }

  response = $cartaotoknzd
  guid = "Q_aq-zlW2rMAQ7f5f7pykxbx-Uo"
}