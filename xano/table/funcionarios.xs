table funcionarios {
  auth = false

  schema {
    int id
    text nome_funcionario filters=trim
    text cargo filters=trim
    enum tipo {
      values = ["VENDEDOR", "MECANICO", "GERENTE"]
    }
  
    text contato? filters=trim
    bool ativo?=true
  }

  index = [{type: "primary", field: [{name: "id"}]}]
  guid = "iuj8n8pK8uHYU_a_cH2FONbfpBI"
}