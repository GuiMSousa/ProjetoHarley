// Login and retrieve an authentication token
query "auth/login" verb=POST {
  api_group = "CadastraCliente"

  input {
    email email? filters=trim|lower
    text password?
  }

  stack {
    db.get USER {
      field_name = "email"
      field_value = $input.email
      output = ["id", "created_at", "name", "email", "password"]
    } as $USER
  
    precondition ($USER != null) {
      error = "Invalid Credentials."
    }
  
    security.check_password {
      text_password = $input.password
      hash_password = $USER.password
    } as $pass_result
  
    precondition ($pass_result) {
      error = "Invalid Credentials."
    }
  
    security.create_auth_token {
      table = "USER"
      extras = {}
      expiration = 86400
      id = $USER.id
    } as $authToken
  }

  response = {authToken: $authToken}
  guid = "IZwaiqkhhSTpNlR83ETa3sNNOjs"
}