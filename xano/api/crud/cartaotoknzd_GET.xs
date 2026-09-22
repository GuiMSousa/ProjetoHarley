// Query all CARTAOTOKNZD records
query cartaotoknzd verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query CARTAOTOKNZD {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "CSssBQ3HlCdP-Cd_Sb_nRpqKNn8"
}