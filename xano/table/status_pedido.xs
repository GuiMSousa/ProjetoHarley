// Status possíveis dos Pedidos de Clientes.
table STATUS_PEDIDO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text status? filters=trim
    text status_para? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree|unique"
      field: [
        {name: "status", op: "desc"}
        {name: "status_para", op: "desc"}
      ]
    }
  ]

  guid = "n3uwZrr2dAiHjEo9Wlv9xSOZP6E"
}