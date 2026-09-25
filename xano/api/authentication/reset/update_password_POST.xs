// Troca a senha do usuário autenticado (saneamento pós-Change 7).
// Exige funcionário vinculado ativo (enforce_role) e a senha atual, para que um token
// vazado não permita tomar a conta de forma permanente. Os campos são obrigatórios e,
// como em auth/login e auth/signup, as senhas não passam por trim.
query "reset/update_password" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    text current_password
    text password filters=min:8
    text confirm_password
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check

    precondition ($input.password == $input.confirm_password) {
      error_type = "inputerror"
      error = "A confirmação não confere com a nova senha."
    }

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "password"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Usuário autenticado não encontrado."
    }

    security.check_password {
      text_password = $input.current_password
      hash_password = $user.password
    } as $senha_atual_confere

    precondition ($senha_atual_confere) {
      error_type = "inputerror"
      error = "Senha atual incorreta."
    }

    precondition ($input.password != $input.current_password) {
      error_type = "inputerror"
      error = "A nova senha deve ser diferente da atual."
    }

    db.edit user {
      field_name = "id"
      field_value = $auth.id
      data = {password: $input.password}
    } as $user_atualizado

    // Somente o id: senha, hash e token nunca vão para o log.
    function.run "Quick Start/log_event" {
      input = {
        user_id : $auth.id
        action  : "reset_password"
        metadata: {id: $auth.id}
      }
    } as $event_log
  }

  response = {success: true, message: "Senha atualizada."}
  tags = ["xano:quick-start"]
  guid = "cbPQPWYP9vhreyzVjayK97AeAfo"
}
