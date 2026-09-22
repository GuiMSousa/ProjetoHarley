// Edit TOKENS record
query "tokens/{tokens_id}" verb=PATCH {
  api_group = "Members & Accounts"

  input {
    int tokens_id? filters=min:1
    dblink {
      table = ""
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch "" {
      field_name = "id"
      field_value = $input.tokens_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $tokens
  }

  response = $tokens
  guid = "VkOsBq2JDbfO-69CY6EFJbAfiSE"
}