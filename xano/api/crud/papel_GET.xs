// Query all PAPEL records
query papel verb=GET {
  api_group = "Crud"

  input {
  }

  stack {
    db.query PAPEL {
      return = {type: "list"}
    } as $model
  }

  response = $model
  guid = "IYEfmc_t_WNYCKFYxzPiezW1DA8"
}