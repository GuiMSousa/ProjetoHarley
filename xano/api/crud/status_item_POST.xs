// Add STATUS_ITEM record
query status_item verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_ITEM"
    }
  }

  stack {
    db.add STATUS_ITEM {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "5aW805OGLAfsq6XG3ZGf4uAUjVQ"
}