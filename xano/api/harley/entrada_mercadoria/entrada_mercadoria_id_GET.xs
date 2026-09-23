// Get entrada_mercadoria record
query "entrada_mercadoria/{entrada_mercadoria_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int entrada_mercadoria_id? filters=min:1
  }

  stack {
    db.get entrada_mercadoria {
      field_name = "id"
      field_value = $input.entrada_mercadoria_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "K_3T6zhmIleV3VOmFVI9__X0OsU"
}