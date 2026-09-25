// Abre uma ordem de serviço. A OS nasce sempre ABERTA; autoria vem do JWT e o cliente, da moto.
query ordens_servico verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int id_moto_cliente filters=min:1

    // Opcional: quando ausente e o autor é MECANICO, ele próprio é o responsável.
    int? id_mecanico? filters=min:1

    enum tipo_servico {
      values = ["PREVENTIVA", "CORRETIVA"]
    }

    text descricao_problema filters=trim
    int? quilometragem? filters=min:0
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

    var $id_mecanico {
      value = $input.id_mecanico
    }

    conditional {
      if ($id_mecanico == null && $role_check.tipo == "MECANICO") {
        var.update $id_mecanico {
          value = $auth_user.id_funcionario
        }
      }
    }

    precondition ($id_mecanico != null) {
      error_type = "inputerror"
      error = "Informe o mecânico responsável."
    }

    db.transaction {
      stack {
        db.get motos_clientes {
          field_name = "id"
          field_value = $input.id_moto_cliente
          output = ["id", "id_cliente", "ativo"]
        } as $moto

        precondition ($moto != null && $moto.ativo != false) {
          error_type = "inputerror"
          error = "Moto do cliente inativa ou inexistente."
        }

        db.get clientes {
          field_name = "id"
          field_value = $moto.id_cliente
          output = ["id", "ativo"]
        } as $cliente

        precondition ($cliente != null && $cliente.ativo != false) {
          error_type = "inputerror"
          error = "Cliente da moto inativo ou inexistente."
        }

        db.get funcionarios {
          field_name = "id"
          field_value = $id_mecanico
          output = ["id", "tipo", "ativo"]
        } as $mecanico

        precondition ($mecanico != null && $mecanico.ativo != false && $mecanico.tipo == "MECANICO") {
          error_type = "inputerror"
          error = "Mecânico responsável inválido ou inativo."
        }

        db.query ordens_servico {
          where = $db.ordens_servico.id_moto_cliente == $input.id_moto_cliente && ($db.ordens_servico.status == "ABERTA" || $db.ordens_servico.status == "EM_ANDAMENTO")
          return = {type: "single"}
        } as $os_em_aberto

        precondition ($os_em_aberto == null) {
          error_type = "inputerror"
          error = "Esta moto já possui uma OS em aberto (nº " ~ $os_em_aberto.id ~ ")."
        }

        db.add ordens_servico {
          data = {
            id_moto_cliente   : $input.id_moto_cliente
            id_cliente        : $moto.id_cliente
            id_funcionario    : $auth_user.id_funcionario
            id_mecanico       : $id_mecanico
            tipo_servico      : $input.tipo_servico
            descricao_problema: $input.descricao_problema
            quilometragem     : $input.quilometragem
            data_abertura     : now
            status            : "ABERTA"
          }
        } as $os

        db.add historico_status_os {
          data = {
            id_os          : $os.id
            status_anterior: null
            status_novo    : "ABERTA"
            id_funcionario : $auth_user.id_funcionario
            created_at     : now
            observacao     : null
          }
        } as $historico
      }
    }

    function.run "Oficina/detalhe_os" {
      input = {os_id: $os.id}
    } as $detalhe
  }

  response = $detalhe
  guid = "DyEE-A-diZBjYzddjNJc5pqbVV8"
}
