// Add funcionarios record
query funcionarios verb=POST {
  api_group = "HARLEY"

  input {
    dblink {
      table = "funcionarios"
    }
  }

  stack {
    db.add funcionarios {
      enforce_hidden_fields = false
      data = {
        nome_funcionario: $input.nome_funcionario
        cargo           : $input.cargo
        tipo            : $input.tipo
        contato         : $input.contato
      }
    } as $model
  }

  response = $model
  guid = "6R5LUqQdOr05ReOMleMUj0JuNsc"
}