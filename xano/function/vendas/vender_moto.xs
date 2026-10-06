// Venda de uma moto do estoque, em uma única transação:
//   1. valida a disponibilidade (não vendida; se reservada, só para o cliente da reserva);
//   2. cria a moto do cliente em motos_clientes;
//   3. registra a transação financeira MOTO em transacoes;
//   4-5. grava historico_status_moto e passa a unidade a VENDIDA por Vendas/transicionar_moto,
//        cuja versão (índice único id_moto + versao_anterior) impede duas vendas simultâneas.
// Chamada por POST vender_moto, que resolve id_funcionario a partir do usuário autenticado.
function "Vendas/vender_moto" {
  input {
    int id_moto filters=min:1
    int id_cliente filters=min:1
    int id_funcionario filters=min:1
    text placa filters=trim|upper
    decimal valor_venda filters=min:0.01
    text? observacao? filters=trim|max:500
  }

  stack {
    // Pré-checagens fora da transação: mensagens específicas.
    db.get motos {
      field_name = "id"
      field_value = $input.id_moto
      output = ["id", "status", "modelo", "marca", "chassi", "clientes_id"]
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    var $status_atual {
      value = $moto.status ?? "DISPONIVEL"
    }

    precondition ($status_atual != "VENDIDA") {
      error_type = "inputerror"
      error = "Esta moto já foi vendida."
    }

    precondition ($status_atual != "RESERVADA" || $moto.clientes_id == $input.id_cliente) {
      error_type = "inputerror"
      error = "Esta moto está reservada para outro cliente."
    }

    precondition ($moto.chassi != null) {
      error_type = "inputerror"
      error = "Cadastre o chassi desta moto antes de vendê-la."
    }

    db.get clientes {
      field_name = "id"
      field_value = $input.id_cliente
      output = ["id", "ativo"]
    } as $cliente

    precondition ($cliente != null && $cliente.ativo != false) {
      error_type = "inputerror"
      error = "Cliente inativo ou inexistente."
    }

    db.query motos_clientes {
      where = $db.motos_clientes.placa == $input.placa || $db.motos_clientes.chassi == $moto.chassi
      return = {type: "exists"}
    } as $ja_cadastrada

    precondition (!$ja_cadastrada) {
      error_type = "inputerror"
      error = "Placa ou chassi já cadastrados em uma moto de cliente."
    }

    try_catch {
      try {
        db.transaction {
          stack {
            // 2. Registrar o veículo no perfil do cliente.
            db.add motos_clientes {
              data = {
                id_cliente: $input.id_cliente
                modelo    : ($moto.modelo ?? $moto.marca) ?? "Harley-Davidson"
                placa     : $input.placa
                chassi    : $moto.chassi
                ativo     : true
              }
            } as $moto_cliente

            // 3. Criar o registro financeiro da venda.
            db.add transacoes {
              data = {
                tipo_transacao : "MOTO"
                id_funcionario : $input.id_funcionario
                id_cliente     : $input.id_cliente
                id_moto_cliente: $moto_cliente.id
                data_transacao : now
                valor_total    : $input.valor_venda
              }
            } as $transacao

            // 4-5. Histórico versionado e status VENDIDA (com o comprador em clientes_id).
            function.run "Vendas/transicionar_moto" {
              input = {
                id_moto       : $input.id_moto
                status_esperado: $status_atual
                status_novo   : "VENDIDA"
                id_funcionario: $input.id_funcionario
                id_cliente    : $input.id_cliente
                observacao    : $input.observacao ?? "Venda"
              }
            } as $historico
          }
        }
      }

      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "A moto foi alterada por outro usuário. Atualize e tente novamente."
        }
      }
    }
  }

  response = {
    id_transacao   : $transacao.id
    id_moto_cliente: $moto_cliente.id
    status         : "SUCESSO"
  }

  guid = "bbLtfcXGVugAEOapQ2KHv8m2bcs"
}
