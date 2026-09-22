// Get CARTAOTOKNZD record
query "cartaotoknzd/{cartaotoknzd_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int cartaotoknzd_id? filters=min:1
  }

  stack {
    db.get CARTAOTOKNZD {
      field_name = "id"
      field_value = $input.cartaotoknzd_id
    } as $cartaotoknzd
  
    precondition ($cartaotoknzd != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $cartaotoknzd
  guid = "7zAoK8ZXugnovdU-sf7-3Mf117w"
}