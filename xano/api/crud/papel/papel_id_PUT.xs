// Update PAPEL record
query "papel/{papel_id}" verb=PUT {
  api_group = "Crud"

  input {
    int papel_id? filters=min:1
    dblink {
      table = "PAPEL"
    }
  }

  stack {
    db.edit PAPEL {
      field_name = "id"
      field_value = $input.papel_id
      enforce_hidden_fields = false
      data = {papel: $input.papel}
    } as $model
  }

  response = $model
  guid = "OffZFd8kr4slUUgWFMkBF9wL3rA"
}