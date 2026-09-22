// Add STATUS_TTOKENIZACAO record
query status_ttokenizacao verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  stack {
    db.add STATUS_TTOKENIZACAO {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "O_5ijlEPYPwIohqDmzYTg_d2fyU"
}