// Add funcionarios record
query funcionarios verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "funcionarios"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
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