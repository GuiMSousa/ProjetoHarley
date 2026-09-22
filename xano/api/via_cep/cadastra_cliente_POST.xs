query CadastraCliente verb=POST {
  api_group = "ViaCEP"

  input {
    text nome? filters=trim
    text senha? filters=trim
    text email? filters=trim
    text celular? filters=trim
    text cpf? filters=trim
    text status_cliente? filters=trim
  }

  stack {
    //  Api de cadastro 
    //
  
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:uxRpeC1O/auth/signup"
      method = "POST"
      params = {
        name    : $input.nome
        email   : $input.email
        password: $input.senha
      }
    
      headers = ["Content-Type: application/json"]
    } as $api1
  
    //  Api  user token
    //
  
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:Dj2TkYUt/auth/me"
      method = "GET"
      params = `$var.api1.response.result.authToken`
      headers = [
        "Authorization: Bearer " ~ $var.api1.response.result.authToken
        "Content-Type:application/json"
      ]
    
    } as $api2
  
    // Bucas status tabela cliente
  
    db.query STATUS_CLIENTE {
      where = $input.status_cliente == $db.STATUS_CLIENTE.status
      return = {type: "list"}
    } as $STATUS_CLIENTE1
  
    db.add CLIENTE {
      enforce_hidden_fields = false
      data = {
        id               : null
        created_at       : "now"
        celular          : $input.celular
        cpf              : $input.cpf
        status_cliente_id: $var.STATUS_CLIENTE1[0].id
        user_id          : `$var.api2.response.result.id`
      }
    } as $CLIENTE1
  }

  response = {
    user     : $api2.response.result
    cliente  : $CLIENTE1
    authToken: $api1.response.result.authToken
  }

  guid = "VG-D5q0Y4Ehjk5JulpewfTN8rT4"
}