// Add STATUS_OP record
query status_op verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_OP"
    }
  }

  stack {
    db.add STATUS_OP {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "fEGl_Bb2CQV3NyFBDpzFRymK8HE"
}