// Get PAPEL record
query "papel/{papel_id}" verb=GET {
  api_group = "Crud"

  input {
    int papel_id? filters=min:1
  }

  stack {
    db.get PAPEL {
      field_name = "id"
      field_value = $input.papel_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "2wlHpFUta5SzWSC9S0uPrBfUsLU"
}