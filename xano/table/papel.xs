// Papéis possíveis para os Usuários cadastrados no sistema.
table PAPEL {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text papel? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "papel", op: "desc"}]}
  ]

  guid = "5Ex_VRKWVKThFndzIfFfzefm-OY"
}