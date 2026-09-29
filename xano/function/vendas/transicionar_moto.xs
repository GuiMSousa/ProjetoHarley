// Único ponto que altera motos.status, reutilizado por reserva e cancelamento (e pela venda,
// na Change 9). Deve ser chamada DENTRO da db.transaction de quem a invoca.
// Concorrência: grava o histórico com versao_anterior antes da moto; o índice único
// (id_moto, versao_anterior) faz a segunda transição concorrente falhar e desfazer tudo.
function "Vendas/transicionar_moto" {
  input {
    int id_moto filters=min:1
    enum status_esperado {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    enum status_novo {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    int id_funcionario filters=min:1

    // Reserva: cliente, vendedor e validade. Cancelamento: todos nulos.
    int? id_cliente?
    int? id_vendedor_reserva?
    timestamp? reservada_ate?
    text? observacao?
  }

  stack {
    db.get motos {
      field_name = "id"
      field_value = $input.id_moto
      output = ["id", "status", "versao_status"]
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    precondition (($moto.status ?? "DISPONIVEL") == $input.status_esperado) {
      error_type = "inputerror"
      error = "A moto foi alterada por outro usuário. Atualize e tente novamente."
    }

    var $versao {
      value = $moto.versao_status ?? 0
    }

    // O histórico é gravado antes da moto: o índice único serializa transições concorrentes.
    db.add historico_status_moto {
      data = {
        id_moto        : $input.id_moto
        status_anterior: $input.status_esperado
        status_novo    : $input.status_novo
        versao_anterior: $versao
        id_funcionario : $input.id_funcionario
        id_cliente     : $input.id_cliente
        observacao     : $input.observacao
        created_at     : now
      }
    } as $historico

    db.patch motos {
      field_name = "id"
      field_value = $input.id_moto
      data = {
        status             : $input.status_novo
        clientes_id        : $input.id_cliente
        id_vendedor_reserva: $input.id_vendedor_reserva
        reservada_ate      : $input.reservada_ate
        versao_status      : $versao + 1
        atualizado_em      : now
      }
    } as $moto_atualizada
  }

  response = $historico
}
