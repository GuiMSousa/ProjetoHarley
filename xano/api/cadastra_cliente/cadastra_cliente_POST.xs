query CadastraCliente verb=POST {
  api_group = "CadastraCliente"

  input {
    text name? filters=trim
    email email? filters=trim|lower
    password password? {
      sensitive = true
      visibility = "internal"
    }
  
    text cpf? filters=trim
    text celular? filters=trim
    text status_clientes? filters=trim
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:Dj2TkYUt/auth/signup"
      method = "POST"
      params = {
        name    : $input.name
        email   : $input.email
        password: $input.password
      }
    
      headers = ["Content-Type:application/json"]
    } as $api1
  
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:Dj2TkYUt/auth/me"
      method = "GET"
      params = `{ 'authToken' :$var.api1.response.result.authToken`
      headers = [
        "Authorization: Bearer" ~$var.api1.response.result.authToken
        "Content-Type:application/json"
      ]
    
    } as $api2
  
    db.query STATUS_CLIENTE {
      where = $input.status_clientes == $db.STATUS_CLIENTE.status
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

  guid = "xpVO4AfBOghd-jljHcfEIWJCDJk"
}