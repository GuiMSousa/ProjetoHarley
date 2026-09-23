// Update clientes record
query "clientes/{clientes_id}" verb=PUT {
  api_group = "HARLEY"

  input {
    int clientes_id? filters=min:1
    dblink {
      table = "clientes"
    }
  }

  stack {
    db.edit clientes {
      field_name = "id"
      field_value = $input.clientes_id
      enforce_hidden_fields = false
      data = {
        nome_cliente: $input.nome_cliente
        cpf_cnpj    : $input.cpf_cnpj
        telefone    : $input.telefone
        email       : $input.email
        endereco    : $input.endereco
      }
    } as $model
  }

  response = $model
  guid = "uoSPM4r8vobxGiwPV_vnaigO_rk"
}