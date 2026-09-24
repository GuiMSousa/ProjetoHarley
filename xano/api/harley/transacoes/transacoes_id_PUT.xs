// Update transacoes record
query "transacoes/{transacoes_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int transacoes_id? filters=min:1
    dblink {
      table = "transacoes"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      db.edit transacoes {
      field_name = "id"
      field_value = $input.transacoes_id
      enforce_hidden_fields = false
      data = {
        tipo_transacao : $input.tipo_transacao
        id_funcionario : $input.id_funcionario
        id_cliente     : $input.id_cliente
        id_moto_cliente: $input.id_moto_cliente
        data_transacao : $input.data_transacao
        valor_total    : $input.valor_total
      }
    } as $model
  }

  response = $model
  guid = "4ncWcoRGeY_FK5rCzUcleGthum4"
}