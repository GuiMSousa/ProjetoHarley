// Edita uma unidade do estoque (GERENTE, Change 8). Somente cor, ano, preço e chassi são
// aceitos; status, cliente, vendedor e validade da reserva nunca vêm do payload.
query "motos/{motos_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id filters=min:1
    text? chassi? filters=trim|upper|pattern:"^[A-HJ-NPR-Z0-9]{17}$"
    text? cor? filters=trim|min:1|max:60
    int? ano_modelo? filters=min:1990
    decimal? preco_venda? filters=min:0.01
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.get motos {
      field_name = "id"
      field_value = $input.motos_id
      output = ["id", "status", "chassi", "id_modelo"]
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    conditional {
      if ($input.ano_modelo != null) {
        var $ano_limite {
          value = (("now"|to_timestamp|format_timestamp:"Y")|to_int) + 1
        }

        precondition ($input.ano_modelo <= $ano_limite) {
          error_type = "inputerror"
          error = "Ano do modelo inválido."
        }
      }
    }

    conditional {
      if ($input.cor != null && $moto.id_modelo != null) {
        db.get modelos_moto {
          field_name = "id"
          field_value = $moto.id_modelo
          output = ["id", "variacoes_cor"]
        } as $modelo

        precondition ((($modelo.variacoes_cor ?? [])|count) == 0 || (($modelo.variacoes_cor ?? [])|some:$$.nome == $input.cor)) {
          error_type = "inputerror"
          error = "Escolha uma das cores cadastradas para o modelo."
        }
      }
    }

    conditional {
      if ($input.chassi != null && $input.chassi != $moto.chassi) {
        precondition (($moto.status ?? "DISPONIVEL") == "DISPONIVEL") {
          error_type = "inputerror"
          error = "O chassi só pode ser corrigido enquanto a moto está disponível."
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
      }
    }

    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input

    db.patch motos {
      field_name = "id"
      field_value = $input.motos_id
      data = `$input|pick:($raw_input|keys)`|unset:"motos_id"|filter_null|set:"atualizado_em":now
    } as $atualizada

    function.run "Vendas/detalhe_moto" {
      input = {moto_id: $input.motos_id}
    } as $detalhe
  }

  response = $detalhe
  guid = "co0x9ziQKCBPsWAPpmov6mtCp_g"
}
