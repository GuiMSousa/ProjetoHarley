// Painel de administração (Change 18): o GERENTE redefine a senha de outro usuário.
// Recusa, antes de gravar:
//   - o usuário inexistente (404);
//   - o próprio gerente (400), porque a troca da própria senha exige a senha atual (reset/update_password);
//   - o usuário técnico admin (403), que passa por qualquer papel no enforce_role;
//   - o usuário de outro gerente (403), porque um gerente não deve poder assumir a conta de outro.
// A senha não passa por trim, é gravada só como hash e nunca volta na resposta nem no event_log.
query "admin/usuarios/{usuarios_id}/senha" verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int usuarios_id filters=min:1
    text password filters=min:8
    text confirm_password
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $input.usuarios_id
      output = ["id", "name", "email", "role", "id_funcionario"]
    } as $alvo

    precondition ($alvo != null) {
      error_type = "notfound"
      error = "Usuário não encontrado."
    }

    precondition ($input.usuarios_id != $auth.id) {
      error_type = "inputerror"
      error = "Para trocar a sua senha, use a troca de senha do próprio usuário."
    }

    precondition ($alvo.role != "admin") {
      error_type = "accessdenied"
      error = "A senha de um usuário administrador técnico só pode ser redefinida no painel do Xano."
    }

    // Tipo do funcionário do alvo; sem vínculo (ou vínculo quebrado) fica nulo. O db.get só roda com
    // id: com valor nulo, o Xano responde 400 "Missing param: field_value".
    var $tipo_alvo {
      value = null
    }

    conditional {
      if ($alvo.id_funcionario != null) {
        db.get funcionarios {
          field_name = "id"
          field_value = $alvo.id_funcionario
          output = ["id", "tipo"]
        } as $funcionario_alvo

        conditional {
          if ($funcionario_alvo != null) {
            var.update $tipo_alvo {
              value = $funcionario_alvo.tipo
            }
          }
        }
      }
    }

    precondition ($tipo_alvo != "GERENTE") {
      error_type = "accessdenied"
      error = "A senha de outro gerente não pode ser redefinida pelo painel: cada gerente troca a própria senha."
    }

    precondition ($input.password == $input.confirm_password) {
      error_type = "inputerror"
      error = "A confirmação não confere com a nova senha."
    }

    db.edit user {
      field_name = "id"
      field_value = $input.usuarios_id
      data = {password: $input.password}
    } as $usuario_atualizado

    // Só ids: senha, hash e token nunca vão para o log.
    function.run "Quick Start/log_event" {
      input = {
        user_id : $auth.id
        action  : "admin_reset_password"
        metadata: {id_usuario: $alvo.id, id_funcionario: $alvo.id_funcionario, id_gerente: $role_check.id}
      }
    } as $event_log
  }

  response = {id: $alvo.id, name: $alvo.name, email: $alvo.email}
  guid = "B-CeeRGXkogAWBbLLtmAWd0YQb8"
}
