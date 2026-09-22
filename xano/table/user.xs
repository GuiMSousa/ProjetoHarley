// Usuários cadastrados no sistema.
table USER {
  auth = true

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text name? filters=trim
    email email? filters=trim|lower
    password password? {
      sensitive = true
      visibility = "internal"
    }
  
    int papel_id?=6 {
      table = "PAPEL"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "email", op: "desc"}]}
  ]

  guid = "nmefU17NAMHw7e1FvdIZgH0XHyU"
}