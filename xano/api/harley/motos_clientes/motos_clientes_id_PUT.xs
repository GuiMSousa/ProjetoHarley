// Update motos_clientes record
query "motos_clientes/{motos_clientes_id}" verb=PUT {
  api_group = "HARLEY"

  input {
    int motos_clientes_id? filters=min:1
    dblink {
      table = "motos_clientes"
    }
  }

  stack {
    db.edit motos_clientes {
      field_name = "id"
      field_value = $input.motos_clientes_id
      enforce_hidden_fields = false
      data = {
        id_cliente: $input.id_cliente
        modelo    : $input.modelo
        placa     : $input.placa
        chassi    : $input.chassi
      }
    } as $model
  }

  response = $model
  guid = "RvhBcncdGD1__bbnOC1W4yUBI00"
}