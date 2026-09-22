// Status possíveis das Solicitações de Cancelamento.
table STATUS_SOLCANCELAMENTO {
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

  guid = "cE6YrLew6XmFYO4MQY6K7AoPbb0"
}