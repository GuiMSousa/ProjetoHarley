// Edit OP record
query "op/{op_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int op_id? filters=min:1
    dblink {
      table = "OP"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch OP {
      field_name = "id"
      field_value = $input.op_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "wnLcWZ49X89pVQ3ucXaw7R_P2SU"
}