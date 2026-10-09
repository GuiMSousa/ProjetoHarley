// Lança retroativamente a receita ORDEM_SERVICO das OS concluídas antes da Change 10 (D10).
// Idempotente: OS que já têm transação com o mesmo id_os são puladas, então pode ser executada
// de novo sem duplicar. OS com total zero não geram lançamento (D2). Executar pelo Run & Debug,
// informando o funcionário GERENTE responsável pelos lançamentos; nenhum endpoint a chama.
function "Financeiro/lancar_os_concluidas_legadas" {
  input {
    int id_funcionario filters=min:1
  }

  stack {
    db.get funcionarios {
      field_name = "id"
      field_value = $input.id_funcionario
      output = ["id", "tipo", "ativo"]
    } as $gerente

    precondition ($gerente != null && $gerente.ativo != false && $gerente.tipo == "GERENTE") {
      error_type = "inputerror"
      error = "Informe o id de um funcionário GERENTE ativo."
    }

    db.query ordens_servico {
      where = $db.ordens_servico.status == "CONCLUIDA"
      output = ["id", "id_cliente", "id_moto_cliente", "data_abertura", "data_encerramento"]
      sort = {id: "asc"}
      return = {type: "list"}
    } as $concluidas

    var $lancadas {
      value = []
    }

    var $ignoradas {
      value = []
    }

    var $id_cliente {
      value = null
    }

    foreach ($concluidas) {
      each as $os {
        db.query transacoes {
          where = $db.transacoes.id_os == $os.id
          return = {type: "exists"}
        } as $ja_lancada

        conditional {
          if (!$ja_lancada) {
            function.run "Oficina/totais_os" {
              input = {os_id: $os.id}
            } as $totais

            conditional {
              if ($totais.valor_total > 0) {
                // Cliente da OS ou, em OS anteriores à Change 6, o dono da moto.
                var.update $id_cliente {
                  value = $os.id_cliente
                }

                conditional {
                  if ($id_cliente == null) {
                    db.get motos_clientes {
                      field_name = "id"
                      field_value = $os.id_moto_cliente
                      output = ["id", "id_cliente"]
                    } as $moto_da_os

                    var.update $id_cliente {
                      value = $moto_da_os.id_cliente
                    }
                  }
                }

                db.add transacoes {
                  data = {
                    tipo_transacao : "ORDEM_SERVICO"
                    id_funcionario : $input.id_funcionario
                    id_cliente     : $id_cliente
                    id_moto_cliente: $os.id_moto_cliente
                    id_os          : $os.id
                    data_transacao : $os.data_encerramento ?? $os.data_abertura
                    valor_total    : $totais.valor_total
                  }
                } as $transacao

                var.update $lancadas {
                  value = $lancadas|push:$os.id
                }
              }

              else {
                var.update $ignoradas {
                  value = $ignoradas|push:$os.id
                }
              }
            }
          }
        }
      }
    }
  }

  response = {
    lancadas                : $lancadas|count
    ids_lancados            : $lancadas
    ids_ignorados_total_zero: $ignoradas
  }
  guid = "99mnkcgxRr2Iy2a6ijm_5m6P2VQ"
}
