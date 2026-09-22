// Delete OP record.
query "op/{op_id}" verb=DELETE {
  api_group = "Members & Accounts"

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
  guid = "2vedIS7x9q8sff6eIy_1pNbWWyQ"
}