// Monta o detalhe de uma OS: dados enriquecidos, linha do tempo de status, itens, totais e o
// lançamento financeiro da conclusão (id_transacao e data_lancamento, Change 10).
// Os totais são recalculados a partir dos itens (fonte de verdade), o que cobre OS legadas.
// Moto, cliente, autor e mecânico vêm de joins à esquerda numa só consulta (Change 16): um vínculo
// nulo (OS do painel ou legada) dá nome nulo, e não o 400 "Missing param: field_value" do db.get.
function "Oficina/detalhe_os" {
  input {
    int os_id
  }

  stack {
    db.query ordens_servico {
      join = {
        motos_clientes: {
          table: "motos_clientes"
          type : "left"
          where: $db.ordens_servico.id_moto_cliente == $db.motos_clientes.id
        }
        cliente_os: {
          table: "clientes"
          type : "left"
          where: $db.ordens_servico.id_cliente == $db.cliente_os.id
        }
        dono_moto: {
          table: "clientes"
          type : "left"
          where: $db.motos_clientes.id_cliente == $db.dono_moto.id
        }
        autor: {
          table: "funcionarios"
          type : "left"
          where: $db.ordens_servico.id_funcionario == $db.autor.id
        }
        mecanico: {
          table: "funcionarios"
          type : "left"
          where: $db.ordens_servico.id_mecanico == $db.mecanico.id
        }
      }

      where = $db.ordens_servico.id == $input.os_id
      eval = {
        placa           : $db.motos_clientes.placa
        modelo          : $db.motos_clientes.modelo
        nome_funcionario: $db.autor.nome_funcionario
        nome_mecanico   : $db.mecanico.nome_funcionario
        id_cliente_moto : $db.motos_clientes.id_cliente
        nome_cliente_os : $db.cliente_os.nome_cliente
        nome_dono_moto  : $db.dono_moto.nome_cliente
      }

      return = {type: "single"}
    } as $os

    precondition ($os != null) {
      error_type = "notfound"
      error = "Ordem de serviço não encontrada."
    }

    // Cliente fotografado na OS ou, em OS anteriores à Change 6, o dono da moto.
    var $id_cliente {
      value = $os.id_cliente ?? $os.id_cliente_moto
    }

    var $nome_cliente {
      value = $os.nome_cliente_os
    }

    conditional {
      if ($os.id_cliente == null) {
        var.update $nome_cliente {
          value = $os.nome_dono_moto
        }
      }
    }

    db.query historico_status_os {
      join = {
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.historico_status_os.id_funcionario == $db.funcionarios.id
        }
      }

      where = $db.historico_status_os.id_os == $input.os_id
      eval = {
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $historico

    db.query itens_ordem_servico {
      join = {
        produtos: {
          table: "produtos"
          type : "left"
          where: $db.itens_ordem_servico.id_produto == $db.produtos.id
        }
      }

      where = $db.itens_ordem_servico.id_os == $input.os_id
      eval = {
        codigo      : $db.produtos.codigo
        nome_produto: $db.produtos.nome_produto
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $itens

    function.run "Oficina/totais_os" {
      input = {os_id: $input.os_id}
    } as $totais

    // Receita lançada na conclusão (Change 10); nula se a OS não foi faturada. Os campos só são lidos
    // com a transação presente: ler o id de um registro nulo como argumento de filtro respondia 500
    // "Unable to locate var: transacao.id" em toda OS ainda não concluída (2026-11-22).
    db.query transacoes {
      where = $db.transacoes.id_os == $input.os_id
      output = ["id", "data_transacao"]
      return = {type: "single"}
    } as $transacao

    var $id_transacao {
      value = null
    }

    var $data_lancamento {
      value = null
    }

    conditional {
      if ($transacao != null) {
        var.update $id_transacao {
          value = $transacao.id
        }

        var.update $data_lancamento {
          value = $transacao.data_transacao
        }
      }
    }

    var $detalhe {
      value = $os
        |unset:"id_cliente_moto"
        |unset:"nome_cliente_os"
        |unset:"nome_dono_moto"
        |set:"id_cliente":$id_cliente
        |set:"nome_cliente":$nome_cliente
        |set:"historico":$historico
        |set:"itens":$itens
        |set:"valor_pecas":$totais.valor_pecas
        |set:"valor_servicos":$totais.valor_servicos
        |set:"valor_total":$totais.valor_total
        |set:"id_transacao":$id_transacao
        |set:"data_lancamento":$data_lancamento
    }
  }

  response = $detalhe
  guid = "dndP0NUct7g4h2FCmDNAdtHRWqI"
}
