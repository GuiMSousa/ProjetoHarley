table entrada_mercadoria {
  auth = false

  schema {
    int id
    int id_fornecedor {
      table = "fornecedores"
    }

    // Número do documento fiscal; obrigatório no endpoint, opcional para registros legados.
    text numero_documento? filters=trim

    // Funcionário responsável, derivado do usuário autenticado.
    int id_funcionario? {
      table = "funcionarios"
    }

    timestamp data_entrada?=now
    decimal valor_total? filters=min:0.01
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_fornecedor"}]}
    {type: "btree", field: [{name: "id_funcionario"}]}
    {
      type : "btree|unique"
      field: [{name: "id_fornecedor"}, {name: "numero_documento"}]
    }
    {
      type : "btree"
      field: [{name: "data_entrada", op: "desc"}]
    }
  ]

  guid = "zts5RZt-pASg8DBNR3j8d8dSJ0Y"
}
