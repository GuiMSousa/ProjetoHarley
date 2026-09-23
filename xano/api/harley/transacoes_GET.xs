// Query all transacoes records
query transacoes verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query transacoes {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "VIaFQU_ReCZvJFE2rxkooYcCYNE"
}