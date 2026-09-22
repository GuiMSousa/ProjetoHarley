// Update USER record
query "user/{user_id}" verb=PUT {
  api_group = "Crud"

  input {
    int user_id? filters=min:1
    dblink {
      table = "USER"
    }
  }

  stack {
    db.edit USER {
      field_name = "id"
      field_value = $input.user_id
      enforce_hidden_fields = false
      data = {
        name    : $input.name
        email   : $input.email
        papel_id: $input.papel_id
      }
    } as $model
  }

  response = $model
  guid = "itsiVU0L3frvDJzLWfk9hmD8oRc"
}