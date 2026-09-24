table itens_ordem_servico {
  auth = false

  schema {
    int id
    int id_os {
      table = "ordens_servico"
    }
  
    int id_produto {
      table = "produtos"
    }
  
    int quantidade filters=min:1
    decimal valor_total_item filters=min:0.01
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_os"}]}
    {type: "btree", field: [{name: "id_produto"}]}
  ]

  guid = "2ptS59XrsIDuP-5Nr3dXsNt5kVU"
}