// Delete USER record
query "user/{user_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int user_id? filters=min:1
  }

  stack {
    db.del USER {
      field_name = "id"
      field_value = $input.user_id
    }
  }

  response = null
  guid = "1HF0uBgJD5K1R_Yj7j5ZdG1z_U0"
}