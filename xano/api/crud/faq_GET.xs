// Query all FAQ records
query faq verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query FAQ {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "iQC53foFHr2RONNaw54Ey0qSGdA"
}