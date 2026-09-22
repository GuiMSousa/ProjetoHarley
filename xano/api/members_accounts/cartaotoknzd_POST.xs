// Add CARTAOTOKNZD record
query cartaotoknzd verb=POST {
  api_group = "Members & Accounts"

  input {
    dblink {
      table = "CARTAOTOKNZD"
    }
  }

  stack {
    db.add CARTAOTOKNZD {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $cartaotoknzd
  }

  response = $cartaotoknzd
  guid = "5BXUg0nbXcFVFTuWEXhdB_ZIFss"
}