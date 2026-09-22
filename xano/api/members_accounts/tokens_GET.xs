// Query all TOKENS records
query tokens verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query "" {
      return = {type: "list"}
    } as $tokens
  }

  response = $tokens
  guid = "2NIzPObz6KOSjWQrmTFGvwGRftU"
}