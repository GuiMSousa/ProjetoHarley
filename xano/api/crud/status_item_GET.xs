// Query all STATUS_ITEM records
query status_item verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query STATUS_ITEM {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "6Xm41PNF1OEEnqkwRfZ8IO9J4e0"
}