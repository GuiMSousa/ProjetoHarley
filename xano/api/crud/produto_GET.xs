// Query all PRODUTO records
query produto verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query PRODUTO {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "VOWH1fd5it46MVyxxVMryFb5F9U"
}