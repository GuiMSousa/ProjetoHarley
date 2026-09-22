// Get PEDIDO record
query "pedido/{pedido_id}" verb=GET {
  api_group = "Crud"

  input {
    int pedido_id? filters=min:1
  }

  stack {
    db.get PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "KrlS4VVptBJewROpIjFQZdEBz74"
}