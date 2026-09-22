// Update CLIENTE record
query "cliente/{cliente_id}" verb=PUT {
  api_group = "Crud"

  input {
    int cliente_id? filters=min:1
    dblink {
      table = "CLIENTE"
    }
  }

  stack {
    db.edit CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
      enforce_hidden_fields = false
      data = {
        celular          : $input.celular
        cpf              : $input.cpf
        status_cliente_id: $input.status_cliente_id
        user_id          : $input.user_id
      }
    } as $model
  }

  response = $model
  guid = "PZlQgZkMeW6h06RbJodJ_wr-tyo"
}