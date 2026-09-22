// Query all TRANSAÇÃO records
query transa_o verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query "" {
      return = {type: "list"}
    } as $transa_o
  }

  response = $transa_o
  guid = "n7ajZ7DWkf9dCUpqnLhPyR2HoiM"
}