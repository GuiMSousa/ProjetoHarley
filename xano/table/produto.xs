// Produtos cadastrados que podem ser incluídos como Itens de Pedidos dos Cliente.
table PRODUTO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text nome? filters=trim
    text descricao? filters=trim
    int qtd_disp? filters=min:0
  
    // url_imagem deve ser o endereço final da imagem em um site público de hospedagem ( sem tela de login, sem restrições de acesso )
    text url_imagem? filters=trim
  
    decimal preco?
    bool precisa_produzir?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "nome", op: "desc"}]}
  ]

  guid = "oD_BxS2ytwKLs1Lj3pTMJxbQzao"
}