// Get fornecedores record
query "fornecedores/{fornecedores_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int fornecedores_id? filters=min:1
  }

  stack {
    db.get fornecedores {
      field_name = "id"
      field_value = $input.fornecedores_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "GhsqpadNjaQt3GAdRAckY2Sfy6M"
}