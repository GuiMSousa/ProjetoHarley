// Delete CEP record.
query "cep/{cep_id}" verb=DELETE {
  api_group = "Members & Accounts"

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
  guid = "Ba0Dr-2skEMqOUtTPE_-PoeMaTc"
}