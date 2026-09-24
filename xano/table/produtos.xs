table produtos {
  auth = false

  schema {
    int id
    text nome_produto filters=trim
    text descricao? filters=trim
    text categoria filters=trim
    int estoque_qtd? filters=min:0
    decimal preco_venda filters=min:0.01
  }

  index = [{type: "primary", field: [{name: "id"}]}]
  guid = "_Ab_0crFwyY7shr_e8lP93qfX5I"
}