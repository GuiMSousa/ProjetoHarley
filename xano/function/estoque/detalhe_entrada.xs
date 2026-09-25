// Monta o detalhe de uma entrada de mercadoria com nomes e itens enriquecidos.
function "Estoque/detalhe_entrada" {
  input {
    int entrada_id
  }

  stack {
    db.query entrada_mercadoria {
      join = {
        fornecedores: {
          table: "fornecedores"
          type : "left"
          where: $db.entrada_mercadoria.id_fornecedor == $db.fornecedores.id
        }
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.entrada_mercadoria.id_funcionario == $db.funcionarios.id
        }
      }

      where = $db.entrada_mercadoria.id == $input.entrada_id
      eval = {
        nome_fornecedor : $db.fornecedores.nome_fornecedor
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      return = {type: "single"}
    } as $entrada

    precondition ($entrada != null) {
      error_type = "notfound"
      error = "Entrada de mercadoria não encontrada."
    }

    db.query itens_compra_estoque {
      join = {
        produtos: {
          table: "produtos"
          type : "left"
          where: $db.itens_compra_estoque.id_produto == $db.produtos.id
        }
      }

      where = $db.itens_compra_estoque.id_entrada == $input.entrada_id
      eval = {
        codigo      : $db.produtos.codigo
        nome_produto: $db.produtos.nome_produto
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $itens

    var $itens_detalhados {
      value = $itens|map:($$|set:"valor_total_item":($$.quantidade * $$.valor_unitario))
    }

    var $detalhe {
      value = $entrada
        |set:"quantidade_itens":($itens|count)
        |set:"itens":$itens_detalhados
    }
  }

  response = $detalhe
  guid = "ZFO4PNjlY6RMI3s76Or8HcALsJY"
}
