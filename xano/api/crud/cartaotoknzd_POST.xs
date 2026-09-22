// Add CARTAOTOKNZD record
query cartaotoknzd verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "CARTAOTOKNZD"
    }
  }

  stack {
    db.add CARTAOTOKNZD {
      enforce_hidden_fields = false
      data = {
        created_at        : "now"
        cliente_id        : $input.cliente_id
        token             : $input.token
        codigoclienteassas: $input.codigoclienteassas
      }
    } as $model
  }

  response = $model
  guid = "k4oWa97Oi8VSxCzwW6BM9a7An8A"
}