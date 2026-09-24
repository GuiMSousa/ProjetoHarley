// Add produtos record
query produtos verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "produtos"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.add produtos {
      enforce_hidden_fields = false
      data = {
        codigo      : $input.codigo
        nome_produto: $input.nome_produto
        descricao   : $input.descricao
        categoria   : $input.categoria
        estoque_qtd : $input.estoque_qtd
        preco_venda : $input.preco_venda
      }
    } as $model
  }

  response = $model
  guid = "3nh4Gb3oYpV_cA6qwgaQvLxISOw"
}