// Query all ordens_servico records
query ordens_servico verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query ordens_servico {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ejDbmcP8h6RVydMZ06OpqGhtIO0"
}