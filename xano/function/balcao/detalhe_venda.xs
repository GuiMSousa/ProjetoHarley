// Recibo de uma venda no balcão (Change 11): a transação BALCAO com os nomes do cliente e do
// vendedor e os itens com código e nome do produto. Somente leitura; usada por
// POST balcao/vendas na criação e na repetição da chave_venda.
function "Balcao/detalhe_venda" {
  input {
    int id_transacao filters=min:1
  }

  stack {
    db.query transacoes {
      join = {
        clientes: {
          table: "clientes"
          type : "left"
          where: $db.transacoes.id_cliente == $db.clientes.id
        }
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.transacoes.id_funcionario == $db.funcionarios.id
        }
      }

      where = $db.transacoes.id == $input.id_transacao
      eval = {
        nome_cliente    : $db.clientes.nome_cliente
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      return = {type: "single"}
    } as $transacao

    precondition ($transacao != null && $transacao.tipo_transacao == "BALCAO") {
      error_type = "notfound"
      error = "Venda no balcão não encontrada."
    }

    db.query itens_transacao {
      join = {
        produtos: {
          table: "produtos"
          type : "left"
          where: $db.itens_transacao.id_produto == $db.produtos.id
        }
      }

      where = $db.itens_transacao.id_transacao == $input.id_transacao
      eval = {
        codigo      : $db.produtos.codigo
        nome_produto: $db.produtos.nome_produto
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $itens

    var $recibo {
      value = {
        id_transacao    : $transacao.id
        tipo_transacao  : $transacao.tipo_transacao
        data_transacao  : $transacao.data_transacao
        valor_total     : $transacao.valor_total
        id_cliente      : $transacao.id_cliente
        nome_cliente    : $transacao.nome_cliente
        id_funcionario  : $transacao.id_funcionario
        nome_funcionario: $transacao.nome_funcionario
        itens           : $itens
      }
    }
  }

  response = $recibo
  guid = "UAhGQW19QUMXMnUP3rCfxkxCx_A"
}
