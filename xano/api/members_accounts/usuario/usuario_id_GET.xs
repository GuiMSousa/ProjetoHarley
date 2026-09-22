// Get Usuario record
query "usuario/{usuario_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int usuario_id? filters=min:1
  }

  stack {
    db.get "" {
      field_name = "id"
      field_value = $input.usuario_id
    } as $usuario
  
    precondition ($usuario != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $usuario
  guid = "276_hCSOK0buaHjQQHS0-mF5xCQ"
}