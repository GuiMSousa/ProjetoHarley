// Delete STATUS_OP record
query "status_op/{status_op_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int status_op_id? filters=min:1
  }

  stack {
    db.del STATUS_OP {
      field_name = "id"
      field_value = $input.status_op_id
    }
  }

  response = null
  guid = "23RlhIlvh0VaOgmVMKc5DBYGbYQ"
}