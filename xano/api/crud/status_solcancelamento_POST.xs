// Add STATUS_SOLCANCELAMENTO record
query status_solcancelamento verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_SOLCANCELAMENTO"
    }
  }

  stack {
    db.add STATUS_SOLCANCELAMENTO {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "695d4MQHJmvsikPzX5lQKVlo9HY"
}