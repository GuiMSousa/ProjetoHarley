// Bloqueado na Change 8: unidades são editadas somente por PATCH motos/{id} (campos explícitos)
// e o status muda somente pelos endpoints de reserva.
query "motos/{motos_id}" verb=PUT {
  api_group = "HARLEY"
  auth = "user"

  input {
    int motos_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Use PATCH motos/{id} para editar a unidade e os endpoints de reserva para o status."
    }
  }

  response = null
  guid = "2aio88YHrIlhJQycs4iQjoyRqUc"
}
