// Get PRODUTO record
query "produto/{produto_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int produto_id? filters=min:1
  }

  stack {
    db.get PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    } as $produto
  
    precondition ($produto != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $produto
  guid = "lZ6P30KmbGcPEHrswtV6jh7NG48"
}