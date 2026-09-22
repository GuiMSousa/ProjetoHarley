// Add TRANSAÇÃO record
query transa_o verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "TRANSAÇÃO"
    }
  }

  stack {
    db.add "TRANSAÇÃO" {
      enforce_hidden_fields = false
      data = {
        created_at         : "now"
        clienteassas       : $input.clienteassas
        idpayment          : $input.idpayment
        tipo               : $input.tipo
        valor              : $input.valor
        datavenc           : $input.datavenc
        descricao          : $input.descricao
        status_transacao_id: $input.status_transacao_id
      }
    } as $model
  }

  response = $model
  guid = "pheFmnnqmpsS62WGp_LL8bN3U88"
}