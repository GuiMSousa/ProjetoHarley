// Edit STATUS_OP record
query "status_op/{status_op_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int status_op_id? filters=min:1
    dblink {
      table = "STATUS_OP"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_OP {
      field_name = "id"
      field_value = $input.status_op_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "lwSMGnPB7cv4lj7Gy-ls5e1PCQ0"
}