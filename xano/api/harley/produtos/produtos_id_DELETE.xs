// Delete produtos record
query "produtos/{produtos_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int produtos_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del produtos {
      field_name = "id"
      field_value = $input.produtos_id
    }
  }

  response = null
  guid = "I8jkWuLntviLabm25izYANc47X4"
}