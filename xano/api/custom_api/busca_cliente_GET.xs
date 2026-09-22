// dado um AuthToken, devolve dados do cliente.
query BuscaCliente verb=GET {
  api_group = "CustomAPI"

  input {
    // Token de autenticação
    text authtoken? filters=trim
  }

  stack {
    api.request {
      url = `https://x8ki-letl-twmt.n7.xano.io/api:Dj2TkYUt/auth/me`
      method = "GET"
      params = $input.authtoken
      headers = [
        "Authorization: Bearer " ~$input.authtoken
        "Content-Type:application/json"
      ]
    
    } as $api1
  
    conditional {
      if ($api1.response.status == 200) {
        db.get CLIENTE {
          field_name = "user_id"
          field_value = `$var.api1.response.result.id`
        } as $CLIENTE1
      }
    
      else {
        var $CLIENTE1 {
          value = {}
        }
      }
    }
  }

  response = $CLIENTE1
  tags = ["módulo de cadastro de clientes"]
  guid = "jf1kjTSm5nDzpGPdXmPT3_g_lXc"
}