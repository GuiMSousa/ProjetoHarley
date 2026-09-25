table produtos {
  auth = false

  schema {
    int id
    text codigo filters=trim
    text nome_produto filters=trim
    text descricao? filters=trim
    text categoria filters=trim
    int estoque_qtd? filters=min:0
    decimal preco_venda filters=min:0.01
    bool ativo?=true

    // Incrementado por Estoque/movimentar_estoque a cada movimentação; nulo equivale a 0.
    int? versao_estoque? filters=min:0
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "codigo"}]}
  ]
  guid = "_Ab_0crFwyY7shr_e8lP93qfX5I"
}