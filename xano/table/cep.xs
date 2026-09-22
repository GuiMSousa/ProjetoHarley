// CEP dos Clientes cadastrados.
table CEP {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text cep? filters=trim
    text uf? filters=trim
    text cidade? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cep", op: "desc"}]}
  ]

  guid = "o5Nchh7OADVPD-M30gsoveTEUvg"
}