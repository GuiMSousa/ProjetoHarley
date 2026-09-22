// Get the record belonging to the authentication token
query "auth/me" verb=GET {
  api_group = "Authentication"
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
  guid = "3EPo5Gimi1qQODZZ9r_1RoP3btI"
}