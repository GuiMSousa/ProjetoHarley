// Clientes que se cadastraram como User e que podem fazer pedidos.
table CLIENTE {
  auth = true

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text celular? filters=trim
    text cpf? filters=trim
    int status_cliente_id?=1 {
      table = "STATUS_CLIENTE"
    }
  
    int user_id? {
      table = "USER"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cpf", op: "desc"}]}
  ]

  guid = "c4ZfIQK8Jn6xRzw285jfn6qDq-Y"
}