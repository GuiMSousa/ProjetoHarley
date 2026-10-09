// Itens de uma transação comercial (Change 11). Hoje só a venda no balcão (BALCAO).
// Imutáveis: nascem em POST balcao/vendas e não têm rotas genéricas.
table itens_transacao {
  auth = false

  schema {
    int id
    int id_transacao {
      table = "transacoes"
    }

    int id_produto {
      table = "produtos"
    }

    int quantidade filters=min:1

    // Fotografia de produtos.preco_venda no fechamento da venda.
    decimal valor_unitario filters=min:0.01

    decimal valor_total_item filters=min:0.01

    // UUID do carrinho, gerado pelo Reflex: repetir a chave devolve a venda já registrada.
    text chave_venda filters=trim

    timestamp created_at?=now
  }

  // (chave_venda, id_produto) único: um produto por venda e uma venda por chave. Duas
  // gravações simultâneas com a mesma chave não podem ambas passar.
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_transacao"}]}
    {type: "btree", field: [{name: "id_produto"}]}
    {
      type : "btree|unique"
      field: [{name: "chave_venda"}, {name: "id_produto"}]
    }
  ]
  guid = "gBMf0lLBjjid3iFnqk_wGo2jCeQ"
}
