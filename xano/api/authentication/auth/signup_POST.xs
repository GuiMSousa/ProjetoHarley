// Signup and retrieve an authentication token
query "auth/signup" verb=POST {
  api_group = "Authentication"

  input {
    text name?
    email email? filters=lower|trim
    password password?
  }

  stack {
    db.get USER {
      field_name = "email"
      field_value = $input.email
    } as $USER
  
    db.add USER {
      enforce_hidden_fields = false
      data = {
        name    : $input.name
        email   : $input.email
        password: $input.password
      }
    } as $USER
  
    precondition ($USER == null) {
      error_type = "accessdenied"
      error = "This account is already in use."
    }
  
    security.create_auth_token {
      table = "USER"
      extras = {}
      expiration = 86400
      id = $USER.id
    } as $authToken
  }

  response = {authToken: $authToken, USERid: $USER.id}
  guid = "nZFlYjX9mcwsIuaeoR30Te8sjNU"
}