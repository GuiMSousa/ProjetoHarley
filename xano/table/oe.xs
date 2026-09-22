// Ordens de Entrega enviados pelo Setor Pedidos ao Setor de Entregas
table OE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int pedido_id? {
      table = "PEDIDO"
    }
  
    int status_oe_id?=1 {
      table = "STATUS_OE"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "qcEvOaSb-YJYexRC7nnOu7VX2fI"
}