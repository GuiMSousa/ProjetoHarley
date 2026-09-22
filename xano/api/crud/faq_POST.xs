// Add FAQ record
query faq verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "FAQ"
    }
  }

  stack {
    db.add FAQ {
      enforce_hidden_fields = false
      data = {
        created_at: "now"
        pergunta  : $input.pergunta
        resposta  : $input.resposta
      }
    } as $model
  }

  response = $model
  guid = "5QGNQdy342TFEhFMTj8dVpfOdjg"
}