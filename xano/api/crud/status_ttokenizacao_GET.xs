// Query all STATUS_TTOKENIZACAO records
query status_ttokenizacao verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_TTOKENIZACAO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "Twh48_SShOK7jNGDeJPgBFozHWQ"
}