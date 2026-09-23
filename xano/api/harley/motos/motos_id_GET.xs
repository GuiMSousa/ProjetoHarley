// Get motos record
query "motos/{motos_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int motos_id? filters=min:1
  }

  stack {
    db.get motos {
      field_name = "id"
      field_value = $input.motos_id
    } as $motos
  
    precondition ($motos != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $motos
  guid = "WTwEoKXXeg7Gftj_J5gR4eaKw98"
}