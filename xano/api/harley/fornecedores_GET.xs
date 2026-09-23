// Query all fornecedores records
query fornecedores verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query fornecedores {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "f64_SmabpKLmfeu_4hhUJb0LkFA"
}