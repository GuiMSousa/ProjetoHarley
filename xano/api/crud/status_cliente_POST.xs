// Add STATUS_CLIENTE record
query status_cliente verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_CLIENTE"
    }
  }

  stack {
    db.add STATUS_CLIENTE {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "t2RSy-yXp8I-KdcVcZBGmCYaHzM"
}