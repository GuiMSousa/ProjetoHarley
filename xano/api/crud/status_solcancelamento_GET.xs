// Query all STATUS_SOLCANCELAMENTO records
query status_solcancelamento verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_SOLCANCELAMENTO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "dXDdZxRROFEzy-z_F4Lma06Qsoo"
}