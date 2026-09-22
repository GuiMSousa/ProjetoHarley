// Query all ITEM records
query item verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query ITEM {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "oDASBFtg2DOjyyRYEfo1U7QcDgg"
}