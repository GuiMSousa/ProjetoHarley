// Update SOLCANCELAMENTO record
query "solcancelamento/{solcancelamento_id}" verb=PUT {
  api_group = "Crud"

  input {
    int solcancelamento_id? filters=min:1
    dblink {
      table = "SOLCANCELAMENTO"
    }
  }

  stack {
    db.edit SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.solcancelamento_id
      enforce_hidden_fields = false
      data = {
        motivo                   : $input.motivo
        pedido_id                : $input.pedido_id
        status_solcancelamento_id: $input.status_solcancelamento_id
      }
    } as $model
  }

  response = $model
  guid = "_abop-WO9i-FCZN57jiCeqK-AiM"
}