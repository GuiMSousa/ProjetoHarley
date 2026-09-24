// Edit clientes record
query "clientes/{clientes_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int clientes_id? filters=min:1
    dblink {
      table = "clientes"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch clientes {
      field_name = "id"
      field_value = $input.clientes_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "Xfo2hFy_6nLlIvQ6Dc0KlIAEZho"
}