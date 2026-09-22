query Buscacep verb=GET {
  api_group = "ViaCEP"

  input {
    text cep? filters=trim
  }

  stack {
    db.query CEP {
      where = $db.CEP.cep == $input.cep
      return = {type: "list"}
    } as $CEP1
  }

  response = $CEP1
  guid = "6d1yIZgGY2n98VldFbWbGuyAPlg"
}