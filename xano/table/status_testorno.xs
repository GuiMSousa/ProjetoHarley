// Status possíveis das Transações de Externo.
table STATUS_TESTORNO {
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

  guid = "f003ifzKMXVoH1MEhioRuTdUl2w"
}