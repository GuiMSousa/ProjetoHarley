// Update CARTAOTOKNZD record
query "cartaotoknzd/{cartaotoknzd_id}" verb=PUT {
  api_group = "Crud"

  input {
    int cartaotoknzd_id? filters=min:1
    dblink {
      table = "CARTAOTOKNZD"
    }
  }

  stack {
    db.edit CARTAOTOKNZD {
      field_name = "id"
      field_value = $input.cartaotoknzd_id
      enforce_hidden_fields = false
      data = {
        cliente_id        : $input.cliente_id
        token             : $input.token
        codigoclienteassas: $input.codigoclienteassas
      }
    } as $model
  }

  response = $model
  guid = "Lfm5wAtq-92Bo4TX-sWOnrePT_I"
}