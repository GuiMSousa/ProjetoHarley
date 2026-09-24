// Creates a gerente user from deployment-provided credentials.
// The password is supplied at execution time and is never stored in source control.
function "Quick Start/seed_gerente" {
  input {
    email email filters=trim|lower
    text password? filters=min:8
    int id_funcionario
  }

  stack {
    db.get funcionarios {
      field_name = "id"
      field_value = $input.id_funcionario
      output = ["id", "tipo"]
    } as $employee

    precondition ($employee != null && $employee.tipo == "GERENTE") {
      error_type = "inputerror"
      error = "The selected employee must be a GERENTE."
    }

    db.get user {
      field_name = "email"
      field_value = $input.email
      output = ["id"]
    } as $existing_user

    precondition ($existing_user == null) {
      error_type = "inputerror"
      error = "A user with this email already exists."
    }

    db.add user {
      data = {
        created_at    : "now"
        name         : "Gerente inicial"
        email        : $input.email
        password     : $input.password
        role         : "admin"
        id_funcionario: $input.id_funcionario
      }
    } as $user
  }

  response = {id: $user.id, email: $user.email, role: $user.role, id_funcionario: $user.id_funcionario}
}