table ordens_servico {
  auth = false

  schema {
    int id
    int id_moto_cliente {
      table = "motos_clientes"
    }

    // Autor da abertura, derivado do usuário autenticado.
    int id_funcionario {
      table = "funcionarios"
    }

    timestamp data_abertura?=now

    // Status muda somente por POST ordens_servico/{id}/status.
    enum status?=ABERTA {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    // Campos da Change 6: anuláveis para preservar OS anteriores.
    // Dono da moto no momento da abertura (fotografia).
    int? id_cliente? {
      table = "clientes"
    }

    // Mecânico responsável pela execução (distinto do autor).
    int? id_mecanico? {
      table = "funcionarios"
    }

    enum? tipo_servico? {
      values = ["PREVENTIVA", "CORRETIVA"]
    }

    text? descricao_problema? filters=trim
    int? quilometragem? filters=min:0
    timestamp? data_inicio?
    timestamp? data_encerramento?
    text? motivo_cancelamento? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_moto_cliente"}]}
    {type: "btree", field: [{name: "id_funcionario"}]}
    {type: "btree", field: [{name: "status"}]}
    {type: "btree", field: [{name: "id_cliente"}]}
    {type: "btree", field: [{name: "id_mecanico"}]}
    {
      type : "btree"
      field: [{name: "data_abertura", op: "desc"}]
    }
  ]

  guid = "nm97yVinqIIVdy9hfkXBcCkuJ7c"
}
