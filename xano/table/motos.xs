// Tabela de motos para controle de estoque e vendas da concessionária.
table motos {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int clientes_id? {
      table = "clientes"
    }
  
    text marca? filters=trim
    text modelo? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "clientes_id", op: "desc"}]}
  ]

  guid = "7HTEhAwc3Lhjg19mElJ3FM0Rcdo"
}