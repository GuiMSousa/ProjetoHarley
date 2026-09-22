// Update tokens record
query "tokens/{tokens_id}" verb=PUT {
  api_group = "Crud"

  input {
    int tokens_id? filters=min:1
    dblink {
      table = "tokens"
    }
  }

  stack {
    db.edit tokens {
      field_name = "id"
      field_value = $input.tokens_id
      enforce_hidden_fields = false
      data = {plataforma: $input.plataforma, token: $input.token}
    } as $model
  }

  response = $model
  guid = "u4V91_Qi-k6iwHELVakKwcDUi0Y"
}