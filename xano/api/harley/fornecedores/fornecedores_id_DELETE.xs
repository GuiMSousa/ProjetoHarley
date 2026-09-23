// Delete fornecedores record
query "fornecedores/{fornecedores_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int fornecedores_id? filters=min:1
  }

  stack {
    db.del fornecedores {
      field_name = "id"
      field_value = $input.fornecedores_id
    }
  }

  response = null
  guid = "iC8HlhOs89OjMrG0j8VKiFznJ8o"
}