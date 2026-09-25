// Transiciona o status de uma OS pela máquina de estados, com controle otimista e histórico.
// Concorrência: o índice único (id_os, status_anterior) de historico_status_os garante que
// cada OS saia de cada status uma única vez; uma segunda transição simultânea a partir do
// mesmo status viola o índice e desfaz a transação inteira.
query "ordens_servico/{ordens_servico_id}/status" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id filters=min:1

    // Status que o cliente está vendo; a gravação só ocorre se ainda for o status atual.
    enum status_atual {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    enum status_novo {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    text? observacao? filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
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

    db.get ordens_servico {
      field_name = "id"
      field_value = $input.ordens_servico_id
      output = ["id", "status"]
    } as $os

    precondition ($os != null) {
      error_type = "notfound"
      error = "Ordem de serviço não encontrada."
    }

    precondition ($os.status == $input.status_atual) {
      error_type = "inputerror"
      error = "A OS foi alterada por outro usuário. Atualize e tente novamente."
    }

    function.run "Oficina/validar_transicao_os" {
      input = {
        status_atual: $input.status_atual
        status_novo : $input.status_novo
        observacao  : $input.observacao
      }
    } as $transicao_valida

    var $agora {
      value = "now"|to_timestamp
    }

    var $dados {
      value = {status: $input.status_novo}
    }

    conditional {
      if ($input.status_novo == "EM_ANDAMENTO") {
        var.update $dados {
          value = $dados|set:"data_inicio":$agora
        }
      }
      elseif ($input.status_novo == "CONCLUIDA") {
        var.update $dados {
          value = $dados|set:"data_encerramento":$agora
        }
      }
      elseif ($input.status_novo == "CANCELADA") {
        var.update $dados {
          value = $dados
            |set:"data_encerramento":$agora
            |set:"motivo_cancelamento":$input.observacao
        }
      }
    }

    try_catch {
      try {
        db.transaction {
          stack {
            // O histórico é gravado primeiro: o índice único serializa transições concorrentes.
            db.add historico_status_os {
              data = {
                id_os          : $input.ordens_servico_id
                status_anterior: $input.status_atual
                status_novo    : $input.status_novo
                id_funcionario : $auth_user.id_funcionario
                created_at     : now
                observacao     : $input.observacao
              }
            } as $historico

            db.patch ordens_servico {
              field_name = "id"
              field_value = $input.ordens_servico_id
              data = $dados
            } as $os_atualizada
          }
        }
      }

      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "Não foi possível registrar a transição: a OS pode ter sido alterada por outro usuário. Atualize e tente novamente."
        }
      }
    }

    function.run "Oficina/detalhe_os" {
      input = {os_id: $input.ordens_servico_id}
    } as $detalhe
  }

  response = $detalhe
}
