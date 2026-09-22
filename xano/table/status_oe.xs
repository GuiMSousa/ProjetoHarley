// Status possíveis das Ordens de Entrega.
table STATUS_OE {
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

  guid = "HJbQTRBhdztciRol7JnwlFsuONU"
}