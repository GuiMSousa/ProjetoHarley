// Ordens de Produção enviados pelo Setor Pedidos ao Setor Cozinha.
table OP {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int pedido_id? {
      table = "PEDIDO"
    }
  
    int status_op_id?=1 {
      table = "STATUS_OP"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "Ri55cI-ysZ_ruZQsLYuIdumTe9Y"
}