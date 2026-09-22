// Get TOKENS record
query "tokens/{tokens_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int tokens_id? filters=min:1
  }

  stack {
    db.get "" {
      field_name = "id"
      field_value = $input.tokens_id
    } as $tokens
  
    precondition ($tokens != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $tokens
  guid = "2ODy8OJrSww5-mHrl4KDcwI0jE4"
}