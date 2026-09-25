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
      output = ["id", "nome_funcionario", "cargo", "tipo", "contato", "ativo"]
    } as $employee
  }

  response = {user: $user, funcionario: $employee}
  tags = ["xano:quick-start"]
  guid = "WeCOghzXKwqBewUnG88GJJBJWGw"
}