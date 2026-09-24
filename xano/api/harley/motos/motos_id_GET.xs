// Get motos record
query "motos/{motos_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.get motos {
      field_name = "id"
      field_value = $input.motos_id
    } as $motos
  
    precondition ($motos != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $motos
  guid = "WTwEoKXXeg7Gftj_J5gR4eaKw98"
}