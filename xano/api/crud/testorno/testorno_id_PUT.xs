// Update TESTORNO record
query "testorno/{testorno_id}" verb=PUT {
  api_group = "Crud"

  input {
    int testorno_id? filters=min:1
    dblink {
      table = "TESTORNO"
    }
  }

  stack {
    db.edit TESTORNO {
      field_name = "id"
      field_value = $input.testorno_id
      enforce_hidden_fields = false
      data = {
        valor             : $input.valor
        solcancelamento_id: $input.solcancelamento_id
        status_testorno_id: $input.status_testorno_id
      }
    } as $model
  }

  response = $model
  guid = "0mBlVMzY-cs417pa8AhC2zGPXAo"
}