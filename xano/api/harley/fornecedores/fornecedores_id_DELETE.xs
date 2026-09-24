// Delete fornecedores record
query "fornecedores/{fornecedores_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int fornecedores_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del fornecedores {
      field_name = "id"
      field_value = $input.fornecedores_id
    }
  }

  response = null
  guid = "iC8HlhOs89OjMrG0j8VKiFznJ8o"
}