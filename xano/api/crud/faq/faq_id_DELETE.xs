// Delete FAQ record
query "faq/{faq_id}" verb=DELETE {
  api_group = "Crud"

  input {
    int faq_id? filters=min:1
  }

  stack {
    db.del FAQ {
      field_name = "id"
      field_value = $input.faq_id
    }
  }

  response = null
  guid = "JT2oSQ2BfpnO0b-7iTOTLzrsnfw"
}