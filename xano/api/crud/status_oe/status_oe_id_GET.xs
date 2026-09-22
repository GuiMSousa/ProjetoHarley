// Get STATUS_OE record
query "status_oe/{status_oe_id}" verb=GET {
  api_group = "Crud"

  input {
    int status_oe_id? filters=min:1
  }

  stack {
    db.get STATUS_OE {
      field_name = "id"
      field_value = $input.status_oe_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "wW0XFNkQJPoL4rBYWzXm8iq1M0E"
}