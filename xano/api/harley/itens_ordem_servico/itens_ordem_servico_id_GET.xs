// Get itens_ordem_servico record
query "itens_ordem_servico/{itens_ordem_servico_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int itens_ordem_servico_id? filters=min:1
  }

  stack {
    db.get itens_ordem_servico {
      field_name = "id"
      field_value = $input.itens_ordem_servico_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "TXzlHJU5R4o1gmdaFe6Y7mKBw3U"
}