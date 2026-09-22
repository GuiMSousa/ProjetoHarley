// Status possíveis dos Clientes.
table STATUS_CLIENTE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text status? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "status", op: "desc"}]}
  ]

  guid = "fe7_nY7_q9PrzRf8Ji1I9YDNzP0"
}