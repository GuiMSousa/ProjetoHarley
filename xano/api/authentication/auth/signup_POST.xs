// Cria um usuário operacional vinculado a um funcionário (somente GERENTE).
// Não emite token: o novo usuário autentica-se com as próprias credenciais.
query "auth/signup" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    text name?
    email email filters=trim|lower
    text password filters=min:8
    int id_funcionario {
      table = "funcionarios"
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    db.get funcionarios {
      field_name = "id"
      field_value = $input.id_funcionario
      output = ["id", "ativo"]
    } as $employee

    precondition ($employee != null && $employee.ativo != false) {
      error_type = "inputerror"
      error = "O funcionário informado não existe ou está inativo."
    }

    db.query user {
      where = $db.user.id_funcionario == $input.id_funcionario
      return = {type: "exists"}
    } as $employee_has_user

    precondition (!$employee_has_user) {
      error_type = "inputerror"
      error = "O funcionário informado já possui um usuário."
    }

    // Check if a user record with that email exists
    db.get user {
      field_name = "email"
      field_value = $input.email
    } as $user
  
    // Verify that the email being used to sign up is unique
    precondition ($user == null) {
      error_type = "inputerror"
      error = "Já existe um usuário com este email."
    }
  
    // Create a new user record
    db.add user {
      data = {
        created_at: "now"
        name      : $input.name
        email     : $input.email
        password  : $input.password
        id_funcionario: $input.id_funcionario
        role      : "member"
      }
    } as $user
  
    // Create an event log for signup
    function.run "Quick Start/log_event" {
      input = {
        user_id : $user.id
        action  : "signup"
        metadata: {id: $user.id, email: $user.email, role: $user.role}
      }
    } as $event_log
  }

  response = {user_id: $user.id, id_funcionario: $user.id_funcionario}
  tags = ["xano:quick-start"]
  guid = "eKokeeLvnCQlLV83vxYuok8twNI"
}