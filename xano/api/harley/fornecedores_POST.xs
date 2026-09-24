// Add fornecedores record
query fornecedores verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    dblink {
      table = "fornecedores"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.add fornecedores {
      enforce_hidden_fields = false
      data = {
        nome_fornecedor: $input.nome_fornecedor
        cnpj           : $input.cnpj
        contato        : $input.contato
      }
    } as $model
  }

  response = $model
  guid = "aSarJS8lL0RCbwq8xwq8GdtHiKg"
}