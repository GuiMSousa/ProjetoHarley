// Add ENDERECO record
query endereco verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "ENDERECO"
    }
  }

  stack {
    db.add ENDERECO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $endereco
  }

  response = $endereco
  guid = "BekgFoOcZDUcOdoKDl1AlaFBgu4"
}