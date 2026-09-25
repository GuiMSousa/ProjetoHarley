// Itens da OS: peças (baixam estoque na inclusão) e serviços (mão de obra, sem estoque).
table itens_ordem_servico {
  auth = false

  schema {
    int id
    int id_os {
      table = "ordens_servico"
    }
  
    // Obrigatório para PECA e nulo para SERVICO (Change 7).
    int? id_produto? {
      table = "produtos"
    }
  
    int quantidade filters=min:1

    // quantidade × valor_unitario, calculado pelo Xano.
    decimal valor_total_item filters=min:0.01

    // Campos da Change 7: anuláveis para preservar itens anteriores.
    // Nulo em itens legados, lidos como PECA.
    enum? tipo_item? {
      values = ["PECA", "SERVICO"]
    }

    // Descrição do serviço (obrigatória para SERVICO).
    text? descricao? filters=trim

    // Fotografia do preco_venda (PECA) ou valor informado (SERVICO).
    decimal? valor_unitario? filters=min:0.01

    // true quando a inclusão gerou SAIDA_OS; somente esses itens devolvem estoque.
    bool? estoque_baixado?

    // Funcionário que incluiu o item, derivado do usuário autenticado.
    int? id_funcionario? {
      table = "funcionarios"
    }

    timestamp? created_at?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_os"}]}
    {type: "btree", field: [{name: "id_produto"}]}
  ]

  guid = "2ptS59XrsIDuP-5Nr3dXsNt5kVU"
}