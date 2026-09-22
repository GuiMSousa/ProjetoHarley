query upsertCEP verb=POST {
  api_group = "ViaCEP"

  input {
    text cep? filters=trim
    text cidade? filters=trim
    text uf? filters=trim
  }

  stack {
    db.query CEP {
      where = $db.CEP.cep == $input.cep
      return = {type: "list"}
    } as $CEP1
  
    conditional {
      if ($var.CEP1[0].cep == $input.cep) {
        db.patch CEP {
          field_name = "id"
          field_value = $var.CEP1[0].id
          data = {cidade: $input.cidade, uf: $input.uf}
        } as $CEP2
      }
    
      else {
        db.add CEP {
          enforce_hidden_fields = false
          data = {cep: $input.cep, cidade: $input.cidade, uf: $input.uf}
        } as $CEP2
      }
    }
  }

  response = $CEP2
  guid = "0RSSVPiK49rXwMIeW2wtOUt_iRg"
}