query atualizaEndereco verb=PATCH {
  api_group = "ViaCEP"

  input {
    int endereco_id? {
      table = "ENDERECO"
    }
  
    text logradouro? filters=trim
    text numero? filters=trim
    text complemento? filters=trim
    text referencia? filters=trim
    text cep? filters=trim
    text cidade? filters=trim
    text uf? filters=trim
    text padrao? filters=trim
    int cliente_id? {
      table = "CLIENTE"
    }
  
    text bairro? filters=trim
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:uxRpeC1O/upsertCEP"
      method = "POST"
      params = {cep: $input.cep, cidade: $input.cidade, uf: $input.uf}
      headers = ["Content-Type: application/json"]
    } as $api1
  
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:j3JdnI_t/endereco/" ~$input.endereco_id
      method = "PATCH"
      params = {
        endereco_id: $input.endereco_id
        cliente_id : $input.cliente_id
        padrao     : $input.padrao
        cep_id     : $api1.response.result.id
        referencia : $input.referencia
        complemento: $input.complemento
        bairro     : $input.bairro
        numero     : $input.numero
        logradouro : $input.logradouro
      }
    
      headers = ["Content-Type: application/json"]
    } as $api2
  }

  response = ```
    
    {
      "logradouro": $var.api2.response.result.logradouro,
      "numero": $var.api2.response.result.numero,
      "complemento": $var.api2.response.result.complemento,
      "referencia": $var.api2.response.result.referencia,
      "padrao": $var.api2.response.result.padrao,
      "cliente_id": $var.api2.response.result.cliente_id,
      "cep": 
         {
            "cep_id": $var.api1.response.result.id,
            "cidade": $var.api1.response.result.cidade,
            "uf": $var.api1.response.result.uf
          }
    }
    ```
  guid = "QBadKpFZlWFmWExQXZcRAtzOW8c"
}