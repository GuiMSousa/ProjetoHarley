// Add itens_ordem_servico record
query itens_ordem_servico verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "itens_ordem_servico"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check
      db.add itens_ordem_servico {
      enforce_hidden_fields = false
      data = {
        id_os           : $input.id_os
        id_produto      : $input.id_produto
        quantidade      : $input.quantidade
        valor_total_item: $input.valor_total_item
      }
    } as $model
  }

  response = $model
  guid = "9kUTmzonk0E3SjsPRJL3rrjL84Q"
}