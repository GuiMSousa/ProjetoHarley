// Add CEP record
query cep verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "CEP"
    }
  }

  stack {
    db.add CEP {
      enforce_hidden_fields = false
      data = {
        created_at: "now"
        cep       : $input.cep
        uf        : $input.uf
        cidade    : $input.cidade
      }
    } as $model
  }

  response = $model
  guid = "UC4jEfJ7TI6j_icC_Grkw1dQ-bQ"
}