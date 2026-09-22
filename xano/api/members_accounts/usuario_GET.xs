// Query all Usuario records
query usuario verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query "" {
      return = {type: "list"}
    } as $usuario
  }

  response = $usuario
  guid = "sVwtn_ab9M372hCT0w7tMFtjuA4"
}