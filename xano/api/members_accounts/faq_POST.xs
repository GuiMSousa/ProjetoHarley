// Add FAQ record
query faq verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "FAQ"
    }
  }

  stack {
    db.add FAQ {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $faq
  }

  response = $faq
  guid = "WoImuK9zeFojMiIgt56TTHaYYZQ"
}