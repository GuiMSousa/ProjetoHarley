// Query all STATUS_TTOKENIZACAO records
query status_ttokenizacao verb=GET {
  api_group = "Members & Accounts"

  input {
  }

  stack {
    db.query STATUS_TTOKENIZACAO {
      return = {type: "list"}
    } as $status_ttokenizacao
  }

  response = $status_ttokenizacao
  guid = "Bd6xXKNusW3T4e-TvlLk96WZ6yg"
}