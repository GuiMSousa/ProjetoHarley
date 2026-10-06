// Cancela a reserva de uma unidade, que volta a DISPONIVEL (Change 8). Pode cancelar quem
// reservou, um GERENTE ou, depois do vencimento, qualquer vendedor. O motivo é obrigatório.
query "motos/{motos_id}/reserva/cancelar" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id filters=min:1
    text motivo filters=trim|min:1|max:500
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

    db.get motos {
      field_name = "id"
      field_value = $input.motos_id
      output = ["id", "status", "id_vendedor_reserva", "reservada_ate"]
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    precondition ($moto.status == "RESERVADA") {
      error_type = "inputerror"
      error = "Esta moto não está reservada."
    }

    var $vencida {
      value = $moto.reservada_ate != null && $moto.reservada_ate < ("now"|to_timestamp)
    }

    precondition ($role_check.tipo == "GERENTE" || $moto.id_vendedor_reserva == $auth_user.id_funcionario || $vencida) {
      error_type = "accessdenied"
      error = "Somente quem reservou ou um gerente pode cancelar esta reserva antes do vencimento."
    }

    try_catch {
      try {
        db.transaction {
          stack {
            function.run "Vendas/transicionar_moto" {
              input = {
                id_moto        : $input.motos_id
                status_esperado: "RESERVADA"
                status_novo    : "DISPONIVEL"
                id_funcionario : $auth_user.id_funcionario
                observacao     : $input.motivo
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
  guid = "tSaLhwyHRC1bGQdRRaCX_y3FF9w"
}
