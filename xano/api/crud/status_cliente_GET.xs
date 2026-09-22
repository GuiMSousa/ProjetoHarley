// Query all STATUS_CLIENTE records
query status_cliente verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_CLIENTE {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "VVxXb40lDIuMCv9mPrhlTRIVRWQ"
}