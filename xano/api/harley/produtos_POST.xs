// Add produtos record
// O produto nasce com saldo 0 (Change 16): o estoque entra pela entrada de mercadoria, que grava
// o livro de movimentações, e a soma do livro bate com estoque_qtd.
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

    precondition (($input.estoque_qtd ?? 0) == 0) {
      error_type = "inputerror"
      error = "O saldo inicial deve ser 0: o estoque entra pela entrada de mercadoria."
    }

    db.add produtos {
      enforce_hidden_fields = false
      data = {
        codigo      : $input.codigo
        nome_produto: $input.nome_produto
        descricao   : $input.descricao
        categoria   : $input.categoria
        estoque_qtd : 0
        preco_venda : $input.preco_venda
      }
    } as $model
  }

  response = $model
  guid = "3nh4Gb3oYpV_cA6qwgaQvLxISOw"
}