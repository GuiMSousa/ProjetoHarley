// Edita um modelo do catálogo (GERENTE). Somente os campos declarados e enviados são gravados;
// ativo = false retira o modelo do catálogo (soft delete).
query "modelos_moto/{modelos_moto_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int modelos_moto_id filters=min:1
    text? nome_modelo? filters=trim|min:1|max:120
    enum? familia? {
      values = ["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
    }

    text? descricao? filters=trim|max:2000
    decimal? preco_base? filters=min:0.01
    text? imagem_principal? filters=trim|startsWith:"https://"
    object[]? variacoes_cor? {
      schema {
        text nome filters=trim|min:1|max:60
        text hex filters=trim|pattern:"^#[0-9A-Fa-f]{6}$"
        text imagem_url filters=trim|startsWith:"https://"
      }
    }

    bool? destaque?
    bool? ativo?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.get modelos_moto {
      field_name = "id"
      field_value = $input.modelos_moto_id
      output = ["id", "nome_modelo"]
    } as $atual

    precondition ($atual != null) {
      error_type = "notfound"
      error = "Modelo não encontrado."
    }

    precondition ((($input.variacoes_cor ?? [])|count) <= 12) {
      error_type = "inputerror"
      error = "Informe no máximo 12 cores por modelo."
    }

    conditional {
      if ($input.nome_modelo != null && $input.nome_modelo != $atual.nome_modelo) {
        db.query modelos_moto {
          where = $db.modelos_moto.nome_modelo == $input.nome_modelo
          return = {type: "exists"}
        } as $nome_existente

        precondition (!$nome_existente) {
          error_type = "inputerror"
          error = "Já existe um modelo com esse nome."
        }
      }
    }

    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input

    db.patch modelos_moto {
      field_name = "id"
      field_value = $input.modelos_moto_id
      data = `$input|pick:($raw_input|keys)`|unset:"modelos_moto_id"|filter_null
    } as $modelo
  }

  response = $modelo
  guid = "HHIqQuG5n1iIyvjylVNgAjBJv44"
}
