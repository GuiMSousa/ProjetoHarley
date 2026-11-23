// Edita a moto de um cliente (VENDEDOR ou GERENTE). PATCH parcial: só os campos declarados e
// enviados são gravados. Campos opcionais e explícitos: com `dblink`, {"ativo": false} sozinho
// (Desativar) respondia 400 "Missing param", porque o Xano exigia os campos obrigatórios (2026-11-23).
query "motos_clientes/{motos_clientes_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_clientes_id? filters=min:1
    int? id_cliente? {
      table = "clientes"
    }

    text? modelo? filters=trim
    text? placa? filters=trim
    text? chassi? filters=trim
    bool? ativo?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch motos_clientes {
      field_name = "id"
      field_value = $input.motos_clientes_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "HtMusiClhmZPnUnv7zBlp17sSy4"
}