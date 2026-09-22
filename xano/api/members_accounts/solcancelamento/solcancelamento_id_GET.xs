// Get SOLCANCELAMENTO record
query "solcancelamento/{solcancelamento_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int solcancelamento_id? filters=min:1
  }

  stack {
    db.get SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.solcancelamento_id
    } as $solcancelamento
  
    precondition ($solcancelamento != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $solcancelamento
  guid = "L2EcuA4e-6E63SmaPwW5ky5nGjY"
}