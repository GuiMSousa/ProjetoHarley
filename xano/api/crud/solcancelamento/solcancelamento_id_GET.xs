// Get SOLCANCELAMENTO record
query "solcancelamento/{solcancelamento_id}" verb=GET {
  api_group = "Crud"

  input {
    int solcancelamento_id? filters=min:1
  }

  stack {
    db.get SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.solcancelamento_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "_PtzlDii4lNFeschj0HnO4GHEFg"
}