// Query all STATUS_CLIENTE records
query status_cliente verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_CLIENTE {
      return = {type: "list"}
    } as $status_cliente
  }

  response = $status_cliente
  guid = "THHYZ1OkqgipCnaYweAnTjB-UfA"
}