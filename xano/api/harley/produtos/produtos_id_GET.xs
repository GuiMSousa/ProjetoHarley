// Get produtos record
query "produtos/{produtos_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int produtos_id? filters=min:1
  }

  stack {
    db.get produtos {
      field_name = "id"
      field_value = $input.produtos_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "efVppBMuYsxa7TYd6p0qDYkFcP0"
}