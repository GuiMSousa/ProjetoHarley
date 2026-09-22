// Query all TTOKENIZACAO records
query ttokenizacao verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query TTOKENIZACAO {
      return = {type: "list"}
    } as $ttokenizacao
  }

  response = $ttokenizacao
  guid = "WGMDPbln_QIyOXVoefCcQLxvIOQ"
}