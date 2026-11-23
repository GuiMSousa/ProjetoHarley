// Painel de administração (Change 18): auditoria de acessos, somente GERENTE. Lê event_log do mais
// recente para o mais antigo, 25 por página, com o nome do usuário e o do funcionário (left join).
// Filtros opcionais: ação e período (data_inicio/data_fim em milissegundos, até 366 dias, como no
// resumo financeiro). Os filtros nulos são ignorados (==?, >=?, <=?); a ação vazia também.
query "admin/eventos" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int? page? filters=min:1
    text? action? filters=trim
    timestamp? data_inicio?
    timestamp? data_fim?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    conditional {
      if ($input.data_inicio != null && $input.data_fim != null) {
        precondition ($input.data_fim >= $input.data_inicio) {
          error_type = "inputerror"
          error = "O fim do período deve ser igual ou posterior ao início."
        }

        // 366 dias em milissegundos.
        precondition (($input.data_fim - $input.data_inicio) <= 31622400000) {
          error_type = "inputerror"
          error = "O período pode ter no máximo 366 dias."
        }
      }
    }

    var $pagina {
      value = $input.page ?? 1
    }

    var $acao {
      value = $input.action
    }

    conditional {
      if ($acao == "") {
        var.update $acao {
          value = null
        }
      }
    }

    db.query event_log {
      join = {
        usuario: {
          table: "user"
          type : "left"
          where: $db.event_log.user_id == $db.usuario.id
        }
        funcionario: {
          table: "funcionarios"
          type : "left"
          where: $db.usuario.id_funcionario == $db.funcionario.id
        }
      }

      where = $db.event_log.action ==? $acao && $db.event_log.created_at >=? $input.data_inicio && $db.event_log.created_at <=? $input.data_fim
      eval = {
        nome_usuario    : $db.usuario.name
        nome_funcionario: $db.funcionario.nome_funcionario
      }

      sort = {created_at: "desc"}
      return = {
        type  : "list"
        paging: {page: $pagina, per_page: 25, totals: true}
      }
    } as $eventos
  }

  response = $eventos
  guid = "ibdBFbT25uQoKu-p8lcr4R4IKkg"
}
