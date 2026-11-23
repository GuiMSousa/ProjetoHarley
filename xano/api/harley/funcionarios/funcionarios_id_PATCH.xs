// Edita um funcionário (GERENTE). PATCH parcial: só os campos declarados e enviados são gravados.
// Campos opcionais e explícitos: com `dblink`, o Xano exigia todos os campos obrigatórios da
// tabela, e {"ativo": false} sozinho respondia 400 "Missing param: nome_funcionario" (2026-11-23).
query "funcionarios/{funcionarios_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int funcionarios_id? filters=min:1
    text? nome_funcionario? filters=trim
    text? cargo? filters=trim
    enum? tipo? {
      values = ["VENDEDOR", "MECANICO", "GERENTE"]
    }

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
  
    db.patch funcionarios {
      field_name = "id"
      field_value = $input.funcionarios_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "-LRpgIR7T4mdtcEco34Hq4AYn7E"
}