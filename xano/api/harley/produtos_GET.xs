// Query all produtos records
query produtos verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check
      db.query produtos {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "ZAIunWDZBYm38BNIOZ3h5SPQeeo"
}