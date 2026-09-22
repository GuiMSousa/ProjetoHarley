// Add tokens record
query tokens verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "tokens"
    }
  }

  stack {
    db.add tokens {
      enforce_hidden_fields = false
      data = {
        created_at: "now"
        plataforma: $input.plataforma
        token     : $input.token
      }
    } as $model
  }

  response = $model
  guid = "FjtTalzF5Ovij7D3qrtMttmbjFs"
}