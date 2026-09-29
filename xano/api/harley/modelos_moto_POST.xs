// Cria um modelo do catálogo (GERENTE). Inputs explícitos: imagens https e cores #RRGGBB.
query modelos_moto verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    text nome_modelo filters=trim|min:1|max:120
    enum familia {
      values = ["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
    }

    text? descricao? filters=trim|max:2000
    decimal preco_base filters=min:0.01
    text imagem_principal filters=trim|startsWith:"https://"
    object[]? variacoes_cor? {
      schema {
        text nome filters=trim|min:1|max:60
        text hex filters=trim|pattern:"^#[0-9A-Fa-f]{6}$"
        text imagem_url filters=trim|startsWith:"https://"
      }
    }

    bool? destaque?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition ((($input.variacoes_cor ?? [])|count) <= 12) {
      error_type = "inputerror"
      error = "Informe no máximo 12 cores por modelo."
    }

    db.query modelos_moto {
      where = $db.modelos_moto.nome_modelo == $input.nome_modelo
      return = {type: "exists"}
    } as $nome_existente

    precondition (!$nome_existente) {
      error_type = "inputerror"
      error = "Já existe um modelo com esse nome."
    }

    db.add modelos_moto {
      data = {
        nome_modelo     : $input.nome_modelo
        familia         : $input.familia
        descricao       : $input.descricao
        preco_base      : $input.preco_base
        imagem_principal: $input.imagem_principal
        variacoes_cor   : $input.variacoes_cor ?? []
        destaque        : $input.destaque ?? false
        ativo           : true
        created_at      : now
      }
    } as $modelo
  }

  response = $modelo
}
