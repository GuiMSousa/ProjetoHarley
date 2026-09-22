table "ordens_servico" {
  auth = false

  schema {
    int id
    int id_moto_cliente {
      table = "motos_clientes"
    }
    int id_funcionario {
      table = "funcionarios"
    }
    timestamp data_abertura?=now
    enum status?="ABERTA" {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_moto_cliente"}]}
    {type: "btree", field: [{name: "id_funcionario"}]}
    {type: "btree", field: [{name: "status"}]}
  ]
  guid = "nm97yVinqIIVdy9hfkXBcCkuJ7c"
}