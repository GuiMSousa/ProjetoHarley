// Bloqueado no saneamento pós-Change 7: exclusão física desabilitada para que registros
// vinculados a OS, estoque, entradas e transações nunca fiquem órfãos.
query "produtos/{produtos_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int produtos_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    precondition (false) {
      error_type = "accessdenied"
      error = "Exclusão física desabilitada: desative o registro (ativo = false)."
    }
  }

  response = null
  guid = "I8jkWuLntviLabm25izYANc47X4"
}
