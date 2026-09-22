// Query all ENDERECO records
query endereco verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query ENDERECO {
      return = {type: "list"}
    } as $endereco
  }

  response = $endereco
  guid = "ANu-gd6SiVkYaiQNFdYZqzJkVX4"
}