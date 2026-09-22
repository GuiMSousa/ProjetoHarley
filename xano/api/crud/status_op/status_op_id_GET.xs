// Get STATUS_OP record
query "status_op/{status_op_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_op_id? filters=min:1
  }

  stack {
    db.get STATUS_OP {
      field_name = "id"
      field_value = $input.status_op_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "SgcpkwROQrOUM8_TDv3woaVr010"
}