// Delete itens_ordem_servico record
query "itens_ordem_servico/{itens_ordem_servico_id}" verb=DELETE {
  api_group = "HARLEY"

  input {
    int itens_ordem_servico_id? filters=min:1
  }

  stack {
    db.del itens_ordem_servico {
      field_name = "id"
      field_value = $input.itens_ordem_servico_id
    }
  }

  response = null
  guid = "RuZEyes7dJzSaYzFlX3c-Nj_p8s"
}