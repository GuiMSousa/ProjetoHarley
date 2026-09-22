// Get the record belonging to the authentication token
query "auth/me" verb=GET {
  api_group = "CadastraCliente"
  auth = "USER"

  input {
  }

  stack {
    db.get USER {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "created_at", "name", "email", "papel_id"]
    } as $USER
  }

  response = $USER
  guid = "-weEALLm2JmJ7nP-V4aBy0TGw9E"
}