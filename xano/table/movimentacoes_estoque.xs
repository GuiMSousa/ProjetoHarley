// Livro de movimentações de estoque (somente inserção). Toda alteração de
// produtos.estoque_qtd passa por Estoque/movimentar_estoque e gera uma linha aqui.
table movimentacoes_estoque {
  auth = false

  schema {
    int id
    int id_produto {
      table = "produtos"
    }

    // O sentido vem do tipo; a quantidade é sempre positiva.
    enum tipo {
      values = ["ENTRADA", "SAIDA_OS", "ESTORNO_OS"]
    }

    int quantidade filters=min:1
    int saldo_anterior filters=min:0
    int saldo_posterior filters=min:0

    // produtos.versao_estoque lida na mesma transação; o produto passa a versao_anterior + 1.
    int versao_anterior filters=min:0

    // Funcionário autenticado que originou a movimentação.
    int id_funcionario {
      table = "funcionarios"
    }

    // Origem ENTRADA.
    int? id_entrada? {
      table = "entrada_mercadoria"
    }

    // Origem SAIDA_OS / ESTORNO_OS.
    int? id_os? {
      table = "ordens_servico"
    }

    // Sem vínculo de tabela: o item pode ser removido depois da movimentação.
    int? id_item_os?

    timestamp created_at?=now
  }

  // O índice único (id_produto, versao_anterior) serializa movimentações concorrentes do
  // mesmo produto: duas transações que leram a mesma versão não podem ambas gravar, e a
  // segunda é desfeita por inteiro.
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_os"}]}

    {
      type : "btree|unique"
      field: [{name: "id_produto"}, {name: "versao_anterior"}]
    }
    {
      type : "btree"
      field: [{name: "created_at", op: "desc"}]
    }
  ]
  guid = "-HIUfJ8l9JBMfE0fC7_-V7LnIVU"
}
