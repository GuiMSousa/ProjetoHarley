// Get ITEM record
query "item/{item_id}" verb=GET {
  api_group = "Crud"

  input {
    int item_id? filters=min:1
  }

  stack {
    db.get ITEM {
      field_name = "id"
      field_value = $input.item_id
    } as $model
  
    precondition ($model != null) {
      error_type = "notfound"
      error = "Not Found"
    }
  }

  response = $model
  guid = "-iSNbr9z5MQEM31xu4tLKcNGAJg"
}