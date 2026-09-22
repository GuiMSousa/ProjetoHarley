// Dado um CEP, atualize se já existir,
// inserir se não existir. Ao final, sempre devolver o
// CEP.
query UpsertCEP verb=POST {
  api_group = "CustomAPI"

  input {
    text cep? filters=trim
    text cidade? filters=trim
    text estado? filters=trim
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
          data = {cidade: $input.cidade, estado: $input.estado}
        } as $CEP2
      }
    
      else {
        db.add CEP {
          enforce_hidden_fields = false
          data = {
            cep   : $input.cep
            uf    : $input.estado
            cidade: $input.cidade
          }
        } as $CEP2
      }
    }
  }

  response = $CEP2
  tags = ["módulo de cadastro de clientes"]
  guid = "7xCGaW_yYqfRaN9Uiuf83DqbXNY"
}