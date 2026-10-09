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

    // OS faturada (Change 10): receita ORDEM_SERVICO gravada na conclusão. Nulo nas demais.
    // Índice simples, não único (D8): a máquina de estados já garante um lançamento por OS.
    int? id_os? {
      table = "ordens_servico"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "tipo_transacao"}]}
    {type: "btree", field: [{name: "id_funcionario"}]}
    {type: "btree", field: [{name: "id_cliente"}]}
    {type: "btree", field: [{name: "id_moto_cliente"}]}
    {type: "btree", field: [{name: "id_os"}]}
    {
      type : "btree"
      field: [{name: "data_transacao", op: "desc"}]
    }
  ]

  guid = "VVu2pfjV1rt6hC79GhA7P25t7_A"
}