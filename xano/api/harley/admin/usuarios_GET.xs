// Painel de administração (Change 18): usuários e o funcionário de cada um, somente GERENTE.
// Cada linha é montada com campos explícitos, então a senha (hash) e o token de recuperação do
// usuário nunca saem, seja qual for o retorno da consulta. Um usuário sem funcionário (criado no
// painel do Xano) sai com os campos do funcionário nulos (left join).
query "admin/usuarios" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.query user {
      join = {
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.user.id_funcionario == $db.funcionarios.id
        }
      }

      eval = {
        nome_funcionario: $db.funcionarios.nome_funcionario
        tipo            : $db.funcionarios.tipo
        cargo           : $db.funcionarios.cargo
        ativo           : $db.funcionarios.ativo
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $usuarios

    var $lista {
      value = []
    }

    var $linha {
      value = {}
    }

    foreach ($usuarios) {
      each as $usuario {
        var.update $linha {
          value = {
            id              : $usuario.id
            name            : $usuario.name
            email           : $usuario.email
            role            : $usuario.role
            created_at      : $usuario.created_at
            id_funcionario  : $usuario.id_funcionario
            nome_funcionario: $usuario.nome_funcionario
            tipo            : $usuario.tipo
            cargo           : $usuario.cargo
            ativo           : $usuario.ativo
          }
        }

        var.update $lista {
          value = $lista|push:$linha
        }
      }
    }
  }

  response = $lista
  guid = "qaEl07jr1o9BKD820xXNSaJE0u0"
}
