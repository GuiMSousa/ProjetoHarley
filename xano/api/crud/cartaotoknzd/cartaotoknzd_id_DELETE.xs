// Delete CARTAOTOKNZD record
query "cartaotoknzd/{cartaotoknzd_id}" verb=DELETE {
  api_group = "Crud"

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
  guid = "XUqgSl9tlx8po7BNdy_hVMloKpo"
}