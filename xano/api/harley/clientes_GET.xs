// Query all clientes records
query clientes verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query clientes {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "JSjBX49SgMggICzYITU94sfo2Hg"
}