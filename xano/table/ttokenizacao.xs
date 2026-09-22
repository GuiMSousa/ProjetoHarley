// Transações de Tokenização dos Cartões de Créditos e Cartões de Débitos.
table TTOKENIZACAO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int cliente_id?
    text? det_cartao_encript? filters=trim
    int status_ttokenizacao_id?=1 {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "Ev1V4B4nhCoFo_v6UTtq3qaeAKQ"
}