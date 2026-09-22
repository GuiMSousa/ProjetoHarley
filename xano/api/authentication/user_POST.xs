// Add USER record
query user verb=POST {
  api_group = "Authentication"

  input {
    dblink {
      table = "USER"
    }
  }

  stack {
    db.add USER {
      enforce_hidden_fields = false
      data = {
        created_at: "now"
        name      : $input.name
        email     : $input.email
        papel_id  : $input.papel_id
      }
    } as $model
  }

  response = $model
  guid = "dxEWVXaLPpGpvZcSQWxjvuBwK7w"
}