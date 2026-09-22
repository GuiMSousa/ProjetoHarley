// Get FAQ record
query "faq/{faq_id}" verb=GET {
  api_group = "Crud"

  input {
    int faq_id? filters=min:1
  }

  stack {
    db.get FAQ {
      field_name = "id"
      field_value = $input.faq_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "FBvfEJoTQWA-ijlZ9g0YDwUP2XA"
}