// Query all itens_ordem_servico records
query itens_ordem_servico verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query itens_ordem_servico {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "6L-m1ZhwAv8DmPKnuKE8Lz4zVKk"
}