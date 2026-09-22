// Delete CARTAOTOKNZD record.
query "cartaotoknzd/{cartaotoknzd_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int cartaotoknzd_id? filters=min:1
  }

  stack {
    db.del CARTAOTOKNZD {
      field_name = "id"
      field_value = $input.cartaotoknzd_id
    }
  }

  response = null
  guid = "2wp3uoyVbhAnDqao9N1PL0KIGMI"
}