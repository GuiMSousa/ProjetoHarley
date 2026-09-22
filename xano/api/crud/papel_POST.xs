// Add PAPEL record
query papel verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "PAPEL"
    }
  }

  stack {
    db.add PAPEL {
      enforce_hidden_fields = false
      data = {created_at: "now", papel: $input.papel}
    } as $model
  }

  response = $model
  guid = "sv4dDZ8FYQa3oOqMSbYdgP65gSU"
}