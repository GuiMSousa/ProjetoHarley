// Delete ITEM record.
query "item/{item_id}" verb=DELETE {
  api_group = "Members & Accounts"

  input {
    int item_id? filters=min:1
  }

  stack {
    db.del ITEM {
      field_name = "id"
      field_value = $input.item_id
    }
  }

  response = null
  guid = "5QUvTLJaZ-Asd_vSspDwFz5n6aY"
}