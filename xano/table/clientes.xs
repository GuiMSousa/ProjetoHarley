table clientes {
  auth = false

  schema {
    int id
    text nome_cliente filters=trim
    text cpf_cnpj filters=trim
    text telefone? filters=trim
    email? email filters=trim|lower
    text endereco? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cpf_cnpj"}]}
  ]

  guid = "A5pGmh311bAq2U1U4s_ENZNHJzA"
}