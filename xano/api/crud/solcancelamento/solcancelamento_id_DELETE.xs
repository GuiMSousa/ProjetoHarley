// Delete SOLCANCELAMENTO record
query "solcancelamento/{solcancelamento_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int solcancelamento_id? filters=min:1
  }

  stack {
    db.del SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.solcancelamento_id
    }
  }

  response = null
  guid = "tnWSF5QxVuK6d8JTWfH2Z_TwVx8"
}