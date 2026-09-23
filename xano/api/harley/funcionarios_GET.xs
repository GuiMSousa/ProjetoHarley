// Query all funcionarios records
query funcionarios verb=GET {
  api_group = "HARLEY"

  input {
  }

  stack {
    db.query funcionarios {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "h70LjpnyCsc0Vof6gUfLN3jOGjc"
}