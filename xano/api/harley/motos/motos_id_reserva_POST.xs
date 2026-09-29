// Reserva uma unidade DISPONIVEL para um cliente ativo (VENDEDOR ou GERENTE, Change 8).
// Vendedor e validade vêm do servidor; a transição passa por Vendas/transicionar_moto, cujo
// índice único de versão garante que duas reservas simultâneas não sejam ambas aceitas.
query "motos/{motos_id}/reserva" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id filters=min:1
    int id_cliente filters=min:1

    // Validade da reserva em dias (1 a 30, padrão 7).
    int? dias_validade? filters=min:1|max:30

    text? observacao? filters=trim|max:500
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id_funcionario"]
    } as $auth_user

    precondition ($auth_user.id_funcionario != null) {
      error_type = "accessdenied"
      error = "Seu usuário não está vinculado a um funcionário."
    }

    // Pré-checagens fora da transação: mensagens específicas.
    db.get motos {
      field_name = "id"
      field_value = $input.motos_id
      output = ["id", "status", "id_modelo"]
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    precondition (($moto.status ?? "DISPONIVEL") == "DISPONIVEL") {
      error_type = "inputerror"
      error = "Esta moto não está disponível para reserva."
    }

    precondition ($moto.id_modelo != null) {
      error_type = "inputerror"
      error = "Cadastre o modelo desta moto antes de reservá-la."
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

    var $validade {
      value = ("now"|to_timestamp)|add_secs_to_timestamp:(($input.dias_validade ?? 7) * 86400)
    }

    try_catch {
      try {
        db.transaction {
          stack {
            function.run "Vendas/transicionar_moto" {
              input = {
                id_moto            : $input.motos_id
                status_esperado    : "DISPONIVEL"
                status_novo        : "RESERVADA"
                id_funcionario     : $auth_user.id_funcionario
                id_cliente         : $input.id_cliente
                id_vendedor_reserva: $auth_user.id_funcionario
                reservada_ate      : $validade
                observacao         : $input.observacao
              }
            } as $transicao
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

    function.run "Vendas/detalhe_moto" {
      input = {moto_id: $input.motos_id}
    } as $detalhe
  }

  response = $detalhe
}
