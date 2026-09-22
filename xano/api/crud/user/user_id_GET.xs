// Get USER record
query "user/{user_id}" verb=GET {
  api_group = "Crud"

  input {
    int user_id? filters=min:1
  }

  stack {
    db.get USER {
      field_name = "id"
      field_value = $input.user_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "VocInfOP56mICE7Q8X0bxqN5lZs"
}