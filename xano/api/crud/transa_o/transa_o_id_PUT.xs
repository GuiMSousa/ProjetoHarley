// Update TRANSAÇÃO record
query "transa_o/{transa_o_id}" verb=PUT {
  api_group = "Crud"

  input {
    int transa_o_id? filters=min:1
    dblink {
      table = "TRANSAÇÃO"
    }
  }

  stack {
    db.edit "TRANSAÇÃO" {
      field_name = "id"
      field_value = $input.transa_o_id
      enforce_hidden_fields = false
      data = {
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
  guid = "IZup4b-jejuLRPft4LnNAzG-ueo"
}