// Edit ITEM record
query "item/{item_id}" verb=PATCH {
  api_group = "Crud"

  input {
    int item_id? filters=min:1
    dblink {
      table = "ITEM"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch ITEM {
      field_name = "id"
      field_value = $input.item_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "lBhTB2BFKqOXp4atBOlE6jF5Y78"
}