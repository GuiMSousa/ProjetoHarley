// Query all TTOKENIZACAO records
query ttokenizacao verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query TTOKENIZACAO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "-MZOMF3tjllyA4mGeQ-LZtFPW4U"
}