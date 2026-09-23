// Add motos_clientes record
query motos_clientes verb=POST {
  api_group = "HARLEY"

  input {
    dblink {
      table = "motos_clientes"
    }
  }

  stack {
    db.add motos_clientes {
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
  guid = "4EkYjmQPx9YIf0QWnHyPMLdFVBc"
}