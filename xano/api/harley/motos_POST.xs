// Cadastra uma unidade no estoque (GERENTE, Change 8). Inputs explícitos: status, cliente e
// vendedor nunca vêm do payload. A unidade nasce DISPONIVEL com a primeira linha de histórico.
query motos verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int id_modelo filters=min:1

    // VIN de 17 caracteres (sem I, O e Q), normalizado em caixa alta.
    text chassi filters=trim|upper|pattern:"^[A-HJ-NPR-Z0-9]{17}$"
    text cor filters=trim|min:1|max:60
    int ano_modelo filters=min:1990
    decimal preco_venda filters=min:0.01
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
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

    var $ano_limite {
      value = (("now"|to_timestamp|format_timestamp:"Y")|to_int) + 1
    }

    precondition ($input.ano_modelo <= $ano_limite) {
      error_type = "inputerror"
      error = "Ano do modelo inválido."
    }

    db.get modelos_moto {
      field_name = "id"
      field_value = $input.id_modelo
      output = ["id", "nome_modelo", "variacoes_cor", "ativo"]
    } as $modelo

    precondition ($modelo != null && $modelo.ativo != false) {
      error_type = "inputerror"
      error = "Modelo inativo ou inexistente."
    }

    precondition ((($modelo.variacoes_cor ?? [])|count) == 0 || (($modelo.variacoes_cor ?? [])|some:$$.nome == $input.cor)) {
      error_type = "inputerror"
      error = "Escolha uma das cores cadastradas para o modelo."
    }

    db.query motos {
      where = $db.motos.chassi == $input.chassi
      return = {type: "exists"}
    } as $chassi_em_estoque

    db.query motos_clientes {
      where = $db.motos_clientes.chassi == $input.chassi
      return = {type: "exists"}
    } as $chassi_de_cliente

    precondition (!$chassi_em_estoque && !$chassi_de_cliente) {
      error_type = "inputerror"
      error = "Este chassi já está cadastrado."
    }

    try_catch {
      try {
        db.transaction {
          stack {
            db.add motos {
              data = {
                id_modelo    : $input.id_modelo
                marca        : "Harley-Davidson"
                modelo       : $modelo.nome_modelo
                chassi       : $input.chassi
                cor          : $input.cor
                ano_modelo   : $input.ano_modelo
                preco_venda  : $input.preco_venda
                status       : "DISPONIVEL"
                versao_status: 1
                atualizado_em: now
                created_at   : now
              }
            } as $moto

            db.add historico_status_moto {
              data = {
                id_moto        : $moto.id
                status_novo    : "DISPONIVEL"
                versao_anterior: 0
                id_funcionario : $auth_user.id_funcionario
                observacao     : "Cadastro da unidade"
                created_at     : now
              }
            } as $historico
          }
        }
      }

      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "Não foi possível cadastrar a moto: o chassi pode ter sido cadastrado por outra operação."
        }
      }
    }

    function.run "Vendas/detalhe_moto" {
      input = {moto_id: $moto.id}
    } as $detalhe
  }

  response = $detalhe
  guid = "S_vB5rNqdGX96LtJUuzpJ_J3038"
}
