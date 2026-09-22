// Add STATUS_OE record
query status_oe verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "STATUS_OE"
    }
  }

  stack {
    db.add STATUS_OE {
      enforce_hidden_fields = false
      data = {created_at: "now", status: $input.status}
    } as $model
  }

  response = $model
  guid = "ubidrh3wyaAgVDQz71jqO6A2FM0"
}