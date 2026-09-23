table fornecedores {
  auth = false

  schema {
    int id
    text nome_fornecedor filters=trim
    text cnpj filters=trim
    text contato? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cnpj"}]}
  ]

  guid = "Nao2gq_N6yXgPEHxZDOBdsT1kcM"
}