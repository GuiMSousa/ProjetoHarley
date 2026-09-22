// Query all PAPEL records
query papel verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query PAPEL {
      return = {type: "list"}
    } as $papel
  }

  response = $papel
  guid = "CsUy5I3DWDIzOEMlTI_zV6Re0BI"
}