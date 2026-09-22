// Query all OE records
query oe verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query OE {
      return = {type: "list"}
    } as $oe
  }

  response = $oe
  guid = "fLRcGAo5e3XAN45z8C3s5oeHOoA"
}