//  Endereços dos Clientes.
table ENDERECO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int cliente_id? {
      table = "CLIENTE"
    }
  
    text? logradouro? filters=trim
    text numero? filters=trim
    text? complemento? filters=trim
    text bairro? filters=trim
    text? referencia? filters=trim
    bool padrao?
    int cep_id? {
      table = "CEP"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "Cba-_nukKBleTdDO7wKdHTaJxRI"
}