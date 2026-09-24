// Update entrada_mercadoria record
query "entrada_mercadoria/{entrada_mercadoria_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int entrada_mercadoria_id? filters=min:1
    dblink {
      table = "entrada_mercadoria"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.edit entrada_mercadoria {
      field_name = "id"
      field_value = $input.entrada_mercadoria_id
      enforce_hidden_fields = false
      data = {
        id_fornecedor: $input.id_fornecedor
        data_entrada : $input.data_entrada
        valor_total  : $input.valor_total
      }
    } as $model
  }

  response = $model
  guid = "EGXNcSO1FjBwMukK1NUtLAtG6H4"
}