// Edit produtos record
query "produtos/{produtos_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int produtos_id? filters=min:1
    dblink {
      table = "produtos"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch produtos {
      field_name = "id"
      field_value = $input.produtos_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "sk8RGWwKFKvwhCb1GNoJO598Qc4"
}