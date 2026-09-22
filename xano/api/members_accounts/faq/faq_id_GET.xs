// Get FAQ record
query "faq/{faq_id}" verb=GET {
  api_group = "Members & Accounts"

  input {
    int faq_id? filters=min:1
  }

  stack {
    db.get FAQ {
      field_name = "id"
      field_value = $input.faq_id
    } as $faq
  
    precondition ($faq != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $faq
  guid = "Qj7OmEk8S48daHfpBSa7ewgjH8Q"
}