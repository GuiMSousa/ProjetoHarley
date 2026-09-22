// Add ENDERECO record
query endereco verb=POST {
  api_group = "SendGrid"

  input {
    dblink {
      table = "ENDERECO"
    }
  }

  stack {
    db.add ENDERECO {
      enforce_hidden_fields = false
      data = {
        created_at : "now"
        cliente_id : $input.cliente_id
        logradouro : $input.logradouro
        numero     : $input.numero
        complemento: $input.complemento
        bairro     : $input.bairro
        referencia : $input.referencia
        padrao     : $input.padrao
        cep_id     : $input.cep_id
      }
    
      addon = [
        {
          name  : "CEP"
          output: ["id", "cep", "uf", "cidade"]
          input : {CEP_id: $output.cep_id}
          as    : "_cep"
        }
      ]
    } as $model
  }

  response = $model
  guid = "jcdejYaXsj8uwaV-O_MI1t5E6Ok"
}