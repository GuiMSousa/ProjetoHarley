// Add SOLCANCELAMENTO record
query solcancelamento verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "SOLCANCELAMENTO"
    }
  }

  stack {
    db.add SOLCANCELAMENTO {
      enforce_hidden_fields = false
      data = {
        created_at               : "now"
        motivo                   : $input.motivo
        pedido_id                : $input.pedido_id
        status_solcancelamento_id: $input.status_solcancelamento_id
      }
    } as $model
  }

  response = $model
  guid = "pNjhqlOWSiHsKU46v3EpoMySXqo"
}