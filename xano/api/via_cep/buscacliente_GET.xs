query buscacliente verb=GET {
  api_group = "ViaCEP"

  input {
    text authtoken? filters=trim
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:Dj2TkYUt/auth/me"
      method = "GET"
      params = $input.authtoken
      headers = [
        "Authorization: Bearer " ~ $input.authtoken
        "Content-Type: application/json"
      ]
    
    } as $api1
  
    conditional {
      if ($api1.response.status == 200) {
        db.get CLIENTE {
          field_name = "user_id"
          field_value = $api1.response.result.id
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
  guid = "qkEVck4BsFxcqgyn-RG0VMm1ZI4"
}