// Delete funcionarios record
query "funcionarios/{funcionarios_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int funcionarios_id? filters=min:1
  }

  stack {
    db.del funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
    }
  }

  response = null
  guid = "2Avyataa5_gqh5nBlh8BQbBcUJE"
}