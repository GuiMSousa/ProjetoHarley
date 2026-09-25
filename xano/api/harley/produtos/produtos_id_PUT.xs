// Update produtos record
query "produtos/{produtos_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int produtos_id? filters=min:1
    dblink {
      table = "produtos"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.edit produtos {
      field_name = "id"
      field_value = $input.produtos_id
      enforce_hidden_fields = false
      data = {
        nome_produto: $input.nome_produto
        descricao   : $input.descricao
        categoria   : $input.categoria
        preco_venda : $input.preco_venda
      }
    } as $model
  }

  response = $model
  guid = "wc1ih4GYqbagSrryy6jUNVfDJ20"
}