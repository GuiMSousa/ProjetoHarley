// Lista mínima de mecânicos ativos (id e nome) para escolher o responsável de uma OS.
query "oficina/mecanicos" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "MECANICO"}
    } as $role_check

    db.query funcionarios {
      where = $db.funcionarios.tipo == "MECANICO" && $db.funcionarios.ativo != false
      sort = {nome_funcionario: "asc"}
      return = {type: "list"}
    } as $mecanicos

    var $model {
      value = $mecanicos|map:{id: $$.id, nome_funcionario: $$.nome_funcionario}
    }
  }

  response = $model
}
