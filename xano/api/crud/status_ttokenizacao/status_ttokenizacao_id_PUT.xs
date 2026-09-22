// Update STATUS_TTOKENIZACAO record
query "status_ttokenizacao/{status_ttokenizacao_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_ttokenizacao_id? filters=min:1
    dblink {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  stack {
    db.edit STATUS_TTOKENIZACAO {
      field_name = "id"
      field_value = $input.status_ttokenizacao_id
      enforce_hidden_fields = false
      data = {status: $input.status}
    } as $model
  }

  response = $model
  guid = "5c20JEvCr-D6SpgVFw06TAShx4k"
}