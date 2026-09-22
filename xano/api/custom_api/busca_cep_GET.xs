// Dado um novo CEP, verificar se ele já está presente na tabela CEP.
query BuscaCEP verb=GET {
  api_group = "CustomAPI"

  input {
    // CEP a ser pesquisado.
    text cep? filters=trim
  }

  stack {
    db.query CEP {
      where = $db.CEP.cep == $input.cep
      return = {type: "list"}
    } as $CEP1
  }

  response = $CEP1
  tags = ["módulo de cadastro de clientes"]
  guid = "SHlIFHfgckgk0z1qJr5-aVcH4s8"
}