// Modelos do catálogo para gestão (GERENTE), inclusive inativos.
query modelos_moto verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.query modelos_moto {
      sort = {nome_modelo: "asc"}
      return = {type: "list"}
    } as $modelos
  }

  response = $modelos
  guid = "MULLg1IeaIWZrSfvjKDBoXs2vfQ"
}
