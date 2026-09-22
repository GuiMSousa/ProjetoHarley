query AtualizaEndereco verb=PATCH {
  api_group = "CustomAPI"

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
    text estado? filters=trim
    text padrao? filters=trim
    int cliente_id? {
      table = "CLIENTE"
    }
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:r9mg_9I3/UpsertCEP"
      method = "POST"
      params = {
        cep   : $input.cep
        cidade: $input.cidade
        estado: $input.estado
      }
    
      headers = ["Content-Type: application/json"]
    } as $api1
  }

  response = null
  guid = "VnGfLKEvNK_SMHu4RvgUjps3HkA"
}