// Query all PRODUTO records
query produto verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query PRODUTO {
      return = {type: "list"}
    } as $produto
  }

  response = $produto
  guid = "nO3x9eF2_ZssofkdJ1WOp4EBTGk"
}