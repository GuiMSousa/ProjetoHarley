// Checks the authenticated user's linked domain employee role.
function "Quick Start/enforce_role" {
  input {
    int user_id

    // ALL, GERENTE, VENDEDOR or MECANICO.
    text required_role
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "id_funcionario", "role"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Authenticated user was not found."
    }

    precondition ($user.id_funcionario != null) {
      error_type = "accessdenied"
      error = "A linked employee is required for business operations."
    }

    db.get funcionarios {
      field_name = "id"
      field_value = $user.id_funcionario
      output = ["id", "nome_funcionario", "cargo", "tipo", "contato"]
    } as $employee

    precondition ($employee != null) {
      error_type = "accessdenied"
      error = "The linked employee was not found."
    }

    precondition (
      $input.required_role == "ALL" ||
      $input.required_role == "GERENTE" ||
      $input.required_role == "VENDEDOR" ||
      $input.required_role == "MECANICO"
    ) {
      error_type = "inputerror"
      error = "Invalid required role specified: " ~ $input.required_role
    }

    conditional {
      if (
        ($input.required_role == "GERENTE" && $employee.tipo != "GERENTE") ||
        ($input.required_role == "VENDEDOR" && $employee.tipo != "GERENTE" && $employee.tipo != "VENDEDOR") ||
        ($input.required_role == "MECANICO" && $employee.tipo != "GERENTE" && $employee.tipo != "MECANICO")
      ) {
        throw {
          name = "accessdenied"
          value = "User does not have the required employee role. Required: " ~ $input.required_role ~ ", Actual: " ~ $employee.tipo
        }
      }
    }
  }

  response = $employee
  tags = ["xano:quick-start"]
  guid = "fneBju0BMGn_2IGtLZtZ-eX55iA"
}