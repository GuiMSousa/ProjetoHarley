// Add OE record
query oe verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "OE"
    }
  }

  stack {
    db.add OE {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $oe
  }

  response = $oe
  guid = "_QCV3yS_i0oRaS3As7DPC8UtNNc"
}