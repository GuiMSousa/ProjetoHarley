// Get the user record belonging to the authentication token
query "auth/me" verb=GET {
  api_group = "Authentication"
  auth = "user"

  input {
  }

  stack {
    // Get the user record based on the auth ID
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "created_at", "name", "email", "role", "id_funcionario"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Authenticated user was not found."
    }

    db.get funcionarios {
      field_name = "id"
      field_value = $user.id_funcionario
      output = ["id", "nome_funcionario", "cargo", "tipo", "contato"]
    } as $employee
  
    // Create an event log for get user record
    function.run "Quick Start/log_event" {
      input = {
        user_id : $user.id
        action  : "get_auth_user"
        metadata: {id: $user.id, email: $user.email, role: $user.role, id_funcionario: $user.id_funcionario}
      }
    } as $event_log
  }

  response = {user: $user, funcionario: $employee}
  tags = ["xano:quick-start"]
  guid = "WeCOghzXKwqBewUnG88GJJBJWGw"
}