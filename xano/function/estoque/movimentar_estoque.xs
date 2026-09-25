// Único ponto que altera produtos.estoque_qtd depois da criação do produto.
// Deve ser chamada DENTRO da db.transaction de quem a invoca.
// Concorrência: lê saldo e versão numa única leitura da linha, grava o livro com
// versao_anterior e só então o produto com versao_anterior + 1. O índice único
// (id_produto, versao_anterior) de movimentacoes_estoque faz a segunda movimentação
// concorrente do mesmo produto falhar e desfazer a transação inteira.
function "Estoque/movimentar_estoque" {
  input {
    int id_produto filters=min:1
    enum tipo {
      values = ["ENTRADA", "SAIDA_OS", "ESTORNO_OS"]
    }

    int quantidade filters=min:1
    int id_funcionario filters=min:1
    int? id_entrada?
    int? id_os?
    int? id_item_os?
  }

  stack {
    db.get produtos {
      field_name = "id"
      field_value = $input.id_produto
      output = ["id", "codigo", "estoque_qtd", "versao_estoque", "ativo"]
    } as $produto

    precondition ($produto != null) {
      error_type = "inputerror"
      error = "Produto inativo ou inexistente."
    }

    // Devolver peça a um produto desativado depois da inclusão é permitido.
    precondition ($input.tipo != "SAIDA_OS" || $produto.ativo != false) {
      error_type = "inputerror"
      error = "Produto inativo ou inexistente."
    }

    var $saldo_anterior {
      value = $produto.estoque_qtd ?? 0
    }

    var $versao {
      value = $produto.versao_estoque ?? 0
    }

    var $saldo_posterior {
      value = $saldo_anterior + $input.quantidade
    }

    conditional {
      if ($input.tipo == "SAIDA_OS") {
        var.update $saldo_posterior {
          value = $saldo_anterior - $input.quantidade
        }
      }
    }

    precondition ($saldo_posterior >= 0) {
      error_type = "inputerror"
      error = "Saldo insuficiente para " ~ $produto.codigo ~ ": disponível " ~ $saldo_anterior ~ ", solicitado " ~ $input.quantidade ~ "."
    }

    // O livro é gravado antes do produto: o índice único serializa movimentações concorrentes.
    db.add movimentacoes_estoque {
      data = {
        id_produto     : $input.id_produto
        tipo           : $input.tipo
        quantidade     : $input.quantidade
        saldo_anterior : $saldo_anterior
        saldo_posterior: $saldo_posterior
        versao_anterior: $versao
        id_funcionario : $input.id_funcionario
        id_entrada     : $input.id_entrada
        id_os          : $input.id_os
        id_item_os     : $input.id_item_os
        created_at     : now
      }
    } as $movimento

    db.edit produtos {
      field_name = "id"
      field_value = $input.id_produto
      data = {
        estoque_qtd   : $saldo_posterior
        versao_estoque: $versao + 1
      }
    } as $produto_atualizado
  }

  response = $movimento
}
