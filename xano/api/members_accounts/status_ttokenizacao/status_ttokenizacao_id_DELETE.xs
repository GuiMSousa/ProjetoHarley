// Delete STATUS_TTOKENIZACAO record.
query "status_ttokenizacao/{status_ttokenizacao_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int status_ttokenizacao_id? filters=min:1
  }

  stack {
    db.del STATUS_TTOKENIZACAO {
      field_name = "id"
      field_value = $input.status_ttokenizacao_id
    }
  }

  response = null
  guid = "JnMsmR63S3c1UT7NlfrJSkNpp4Y"
}