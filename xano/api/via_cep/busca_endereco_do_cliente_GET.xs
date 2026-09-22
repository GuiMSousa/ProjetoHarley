query busca_Endereco_do_cliente verb=GET {
  api_group = "ViaCEP"

  input {
    text authtoken? filters=trim
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:uxRpeC1O/buscacliente"
      method = "GET"
      params = {authtoken: $input.authtoken}
      headers = ["Content-Type:application/json"]
    } as $api1
  
    db.query ENDERECO {
      where = `$var.api1.response.result.id` == $db.ENDERECO.cliente_id
      return = {type: "list"}
      output = [
        "id"
        "created_at"
        "cliente_id"
        "logradouro"
        "numero"
        "complemento"
        "bairro"
        "referencia"
        "padrao"
        "cep_id"
      ]
    
      addon = [
        {
          name  : "CEP"
          output: ["id", "created_at", "cep", "uf", "cidade"]
          input : {CEP_id: $output.cep_id}
          as    : "_cep"
        }
      ]
    } as $ENDERECO1
  }

  response = $ENDERECO1
  guid = "pUYHu4MeQjY4j4seqcAliO6ci6A"
}