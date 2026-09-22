// Delete CEP record
query "cep/{cep_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int cep_id? filters=min:1
  }

  stack {
    db.del CEP {
      field_name = "id"
      field_value = $input.cep_id
    }
  }

  response = null
  guid = "B-OIwbufnR5sGG1wVG7c4bHWAR4"
}