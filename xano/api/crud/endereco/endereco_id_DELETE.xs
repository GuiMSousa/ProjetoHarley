// Delete ENDERECO record
query "endereco/{endereco_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int endereco_id? filters=min:1
  }

  stack {
    db.del ENDERECO {
      field_name = "id"
      field_value = $input.endereco_id
    }
  }

  response = null
  guid = "molBd-hEqL2GbLyZkdO7-0ki3ZU"
}