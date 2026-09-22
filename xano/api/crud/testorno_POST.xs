// Add TESTORNO record
query testorno verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "TESTORNO"
    }
  }

  stack {
    db.add TESTORNO {
      enforce_hidden_fields = false
      data = {
        created_at        : "now"
        valor             : $input.valor
        solcancelamento_id: $input.solcancelamento_id
        status_testorno_id: $input.status_testorno_id
      }
    } as $model
  }

  response = $model
  guid = "o4g5yOqgtGWMLOLt8gYxWh9WCqo"
}