// Delete PRODUTO record.
query "produto/{produto_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int produto_id? filters=min:1
  }

  stack {
    db.del PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    }
  }

  response = null
  guid = "OyrvlBc-OEhoJ3pD4rqJ9Rjz0Pw"
}