// Get CEP record
query "cep/{cep_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int cep_id? filters=min:1
  }

  stack {
    db.get CEP {
      field_name = "id"
      field_value = $input.cep_id
    } as $cep
  
    precondition ($cep != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $cep
  guid = "CPIpuXOGVHSXtYRhp0JGJL3ahWA"
}