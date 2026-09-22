// Get OP record
query "op/{op_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int op_id? filters=min:1
  }

  stack {
    db.get OP {
      field_name = "id"
      field_value = $input.op_id
    } as $op
  
    precondition ($op != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $op
  guid = "WLzFdlq1RV5dZiMMTO6malUMw8c"
}