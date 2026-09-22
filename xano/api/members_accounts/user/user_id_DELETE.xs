// Delete USER record.
query "user/{user_id}" verb=DELETE {
  api_group = "Members & Accounts"

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
  guid = "MGO21zcR7VQlualGkaVXkqzF898"
}