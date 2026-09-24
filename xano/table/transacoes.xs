table transacoes {
  auth = false

  schema {
    int id
    enum tipo_transacao {
      values = ["MOTO", "PECAS", "BALCAO", "COMPRA", "ORDEM_SERVICO"]
    }
  
    int id_funcionario {
      table = "funcionarios"
    }
  
    int id_cliente? {
      table = "clientes"
    }
  
    int id_moto_cliente? {
      table = "motos_clientes"
    }
  
    timestamp data_transacao?=now
    decimal valor_total? filters=min:0.01
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "tipo_transacao"}]}
    {type: "btree", field: [{name: "id_funcionario"}]}
    {type: "btree", field: [{name: "id_cliente"}]}
    {type: "btree", field: [{name: "id_moto_cliente"}]}
    {
      type : "btree"
      field: [{name: "data_transacao", op: "desc"}]
    }
  ]

  guid = "VVu2pfjV1rt6hC79GhA7P25t7_A"
}