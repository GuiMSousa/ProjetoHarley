// Add clientes record
query clientes verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "clientes"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      db.add clientes {
      enforce_hidden_fields = false
      data = {
        nome_cliente: $input.nome_cliente
        cpf_cnpj    : $input.cpf_cnpj
        telefone    : $input.telefone
        email       : $input.email
        endereco    : $input.endereco
      }
    } as $model
  }

  response = $model
  guid = "UBqNeuM0JcLFsQbQ9cnqMPFlMkg"
}