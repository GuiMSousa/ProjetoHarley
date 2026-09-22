// Query all STATUS_OE records
query status_oe verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_OE {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "E34PiZ2O8MFq02brm_rbIEGCHp4"
}