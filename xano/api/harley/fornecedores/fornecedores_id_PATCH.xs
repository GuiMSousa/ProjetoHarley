// Edita um fornecedor (GERENTE). PATCH parcial: só os campos declarados e enviados são gravados.
// Campos opcionais e explícitos: com `dblink`, {"ativo": false} sozinho (Desativar) respondia 400
// "Missing param", porque o Xano exigia os campos obrigatórios da tabela (2026-11-23).
query "fornecedores/{fornecedores_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int fornecedores_id? filters=min:1
    text? nome_fornecedor? filters=trim
    text? cnpj? filters=trim
    text? contato? filters=trim
    bool? ativo?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch fornecedores {
      field_name = "id"
      field_value = $input.fornecedores_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "uAjYL5Jp9m1hfzqmunqjbmr4pwQ"
}