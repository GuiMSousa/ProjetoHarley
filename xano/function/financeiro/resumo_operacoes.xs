// Visão consolidada das operações (vw_resumo_operacoes do domínio, Change 10): receitas das
// transações e despesas das entradas de mercadoria num período. Somente leitura.
// Natureza: MOTO, ORDEM_SERVICO, PECAS e BALCAO são RECEITA; COMPRA (lançamentos antigos) e
// ENTRADA_MERCADORIA são DESPESA. As entradas não geram transação COMPRA (D4), então nada conta
// duas vezes. Os totais cobrem o período inteiro; a lista traz as 500 operações mais recentes (D7).
function "Financeiro/resumo_operacoes" {
  input {
    timestamp inicio
    timestamp fim
  }

  stack {
    precondition ($input.fim >= $input.inicio) {
      error_type = "inputerror"
      error = "O fim do período deve ser igual ou posterior ao início."
    }

    // 366 dias em milissegundos.
    precondition (($input.fim - $input.inicio) <= 31622400000) {
      error_type = "inputerror"
      error = "O período pode ter no máximo 366 dias."
    }

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
        motos_clientes: {
          table: "motos_clientes"
          type : "left"
          where: $db.transacoes.id_moto_cliente == $db.motos_clientes.id
        }
      }

      where = $db.transacoes.data_transacao >= $input.inicio && $db.transacoes.data_transacao <= $input.fim
      eval = {
        nome_cliente    : $db.clientes.nome_cliente
        nome_funcionario: $db.funcionarios.nome_funcionario
        modelo          : $db.motos_clientes.modelo
        placa           : $db.motos_clientes.placa
      }

      sort = {data_transacao: "desc"}
      return = {type: "list"}
    } as $transacoes

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

      where = $db.entrada_mercadoria.data_entrada >= $input.inicio && $db.entrada_mercadoria.data_entrada <= $input.fim
      eval = {
        nome_fornecedor : $db.fornecedores.nome_fornecedor
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      sort = {data_entrada: "desc"}
      return = {type: "list"}
    } as $entradas

    var $receitas {
      value = 0
    }

    var $despesas {
      value = 0
    }

    // tipo -> {tipo, natureza, quantidade, valor}
    var $por_tipo {
      value = {}
    }

    var $operacoes {
      value = []
    }

    var $natureza {
      value = "RECEITA"
    }

    var $valor {
      value = 0
    }

    var $acumulado {
      value = null
    }

    var $linha_tipo {
      value = {}
    }

    var $operacao {
      value = {}
    }

    foreach ($transacoes) {
      each as $transacao {
        var.update $natureza {
          value = "RECEITA"
        }

        conditional {
          if ($transacao.tipo_transacao == "COMPRA") {
            var.update $natureza {
              value = "DESPESA"
            }
          }
        }

        var.update $valor {
          value = $transacao.valor_total ?? 0
        }

        conditional {
          if ($natureza == "RECEITA") {
            var.update $receitas {
              value = $receitas + $valor
            }
          }

          else {
            var.update $despesas {
              value = $despesas + $valor
            }
          }
        }

        var.update $acumulado {
          value = $por_tipo|get:$transacao.tipo_transacao:null
        }

        var.update $linha_tipo {
          value = {
            tipo      : $transacao.tipo_transacao
            natureza  : $natureza
            quantidade: ($acumulado.quantidade ?? 0) + 1
            valor     : (($acumulado.valor ?? 0) + $valor)|round:2
          }
        }

        var.update $por_tipo {
          value = $por_tipo|set:$transacao.tipo_transacao:$linha_tipo
        }

        var.update $operacao {
          value = {
            origem          : "TRANSACAO"
            id              : $transacao.id
            tipo            : $transacao.tipo_transacao
            natureza        : $natureza
            data            : $transacao.data_transacao
            valor           : $valor
            contraparte     : $transacao.nome_cliente
            funcionario     : $transacao.nome_funcionario
            id_os           : $transacao.id_os
            id_moto_cliente : $transacao.id_moto_cliente
            modelo          : $transacao.modelo
            placa           : $transacao.placa
            id_entrada      : null
            numero_documento: null
          }
        }

        var.update $operacoes {
          value = $operacoes|push:$operacao
        }
      }
    }

    foreach ($entradas) {
      each as $entrada {
        var.update $valor {
          value = $entrada.valor_total ?? 0
        }

        var.update $despesas {
          value = $despesas + $valor
        }

        var.update $acumulado {
          value = $por_tipo|get:"ENTRADA_MERCADORIA":null
        }

        var.update $linha_tipo {
          value = {
            tipo      : "ENTRADA_MERCADORIA"
            natureza  : "DESPESA"
            quantidade: ($acumulado.quantidade ?? 0) + 1
            valor     : (($acumulado.valor ?? 0) + $valor)|round:2
          }
        }

        var.update $por_tipo {
          value = $por_tipo|set:"ENTRADA_MERCADORIA":$linha_tipo
        }

        var.update $operacao {
          value = {
            origem          : "ENTRADA"
            id              : $entrada.id
            tipo            : "ENTRADA_MERCADORIA"
            natureza        : "DESPESA"
            data            : $entrada.data_entrada
            valor           : $valor
            contraparte     : $entrada.nome_fornecedor
            funcionario     : $entrada.nome_funcionario
            id_os           : null
            id_moto_cliente : null
            modelo          : null
            placa           : null
            id_entrada      : $entrada.id
            numero_documento: $entrada.numero_documento
          }
        }

        var.update $operacoes {
          value = $operacoes|push:$operacao
        }
      }
    }

    var $total_operacoes {
      value = $operacoes|count
    }

    // Mais recentes primeiro; a lista é limitada, os totais não.
    var.update $operacoes {
      value = ($operacoes|sort:"data":"number":false)|slice:0:500
    }
  }

  response = {
    inicio         : $input.inicio
    fim            : $input.fim
    receitas       : $receitas|round:2
    despesas       : $despesas|round:2
    saldo          : ($receitas - $despesas)|round:2
    por_tipo       : $por_tipo|values
    operacoes      : $operacoes
    total_operacoes: $total_operacoes
    truncado       : $total_operacoes > 500
  }
  guid = "mSHDd8CPypUv7vWujMFPj3ORR0A"
}
