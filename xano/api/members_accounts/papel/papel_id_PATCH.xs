// Edit PAPEL record
query "papel/{papel_id}" verb=PATCH {
  api_group = "Members & Accounts"

  input {
    int papel_id? filters=min:1
    dblink {
      table = "PAPEL"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch PAPEL {
      field_name = "id"
      field_value = $input.papel_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $papel
  }

  response = $papel
  guid = "QNSmtpQiiwHu8urbMf90b-MYjxM"
}