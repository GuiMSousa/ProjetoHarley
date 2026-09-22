// Get OP record
query "op/{op_id}" verb=GET {
  api_group = "Crud"

  input {
    int op_id? filters=min:1
  }

  stack {
    db.get OP {
      field_name = "id"
      field_value = $input.op_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "SmoAu0yPM1Db1ZDZGSfhz4dZIds"
}