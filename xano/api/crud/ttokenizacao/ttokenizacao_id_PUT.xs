// Update TTOKENIZACAO record
query "ttokenizacao/{ttokenizacao_id}" verb=PUT {
  api_group = "Crud"

  input {
    int ttokenizacao_id? filters=min:1
    dblink {
      table = "TTOKENIZACAO"
    }
  }

  stack {
    db.edit TTOKENIZACAO {
      field_name = "id"
      field_value = $input.ttokenizacao_id
      enforce_hidden_fields = false
      data = {
        cliente_id            : $input.cliente_id
        det_cartao_encript    : $input.det_cartao_encript
        status_ttokenizacao_id: $input.status_ttokenizacao_id
      }
    } as $model
  }

  response = $model
  guid = "c1fzH-YXnJBOQ2-YJ72T87glVAY"
}