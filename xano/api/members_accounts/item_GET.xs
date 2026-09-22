// Query all ITEM records
query item verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query ITEM {
      return = {type: "list"}
    } as $item
  }

  response = $item
  guid = "K8GCa9cnCdMQ8n6G2s2jH_0NfQY"
}