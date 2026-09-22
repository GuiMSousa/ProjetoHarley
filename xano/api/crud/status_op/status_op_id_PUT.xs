// Update STATUS_OP record
query "status_op/{status_op_id}" verb=PUT {
  api_group = "Crud"

  input {
    int status_op_id? filters=min:1
    dblink {
      table = "STATUS_OP"
    }
  }

  stack {
    db.edit STATUS_OP {
      field_name = "id"
      field_value = $input.status_op_id
      enforce_hidden_fields = false
      data = {status: $input.status}
    } as $model
  }

  response = $model
  guid = "q7D9Q_gl6YXp3RjDuuXnBdjTUuE"
}