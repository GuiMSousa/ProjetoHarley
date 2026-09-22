// Query all USER records
query user verb=GET {
  api_group = "Authentication"

  input {
  }

  stack {
    db.query USER {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "py1EszYwrfc05UK182LFMspOnTo"
}