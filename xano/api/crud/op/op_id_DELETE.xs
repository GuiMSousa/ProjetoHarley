// Delete OP record
query "op/{op_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int op_id? filters=min:1
  }

  stack {
    db.del OP {
      field_name = "id"
      field_value = $input.op_id
    }
  }

  response = null
  guid = "7I26hMy6kuHizMO8XFRJ7rSsLMA"
}