// Query all CLIENTE records
query cliente verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query CLIENTE {
      return = {type: "list"}
    } as $cliente
  }

  response = $cliente
  guid = "2p_eVo-Gnf1Z0HNROM2ui_ZJppI"
}