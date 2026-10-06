// Trilha de auditoria das transições de status das motos do estoque (somente inserção).
table historico_status_moto {
  auth = false

  schema {
    int id
    int id_moto {
      table = "motos"
    }

    // Nulo no cadastro da unidade.
    enum? status_anterior? {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    enum status_novo {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    // motos.versao_status lida na transição; a moto passa a versao_anterior + 1.
    int versao_anterior filters=min:0

    // Funcionário autenticado que executou a transição.
    int id_funcionario {
      table = "funcionarios"
    }

    int? id_cliente? {
      table = "clientes"
    }

    text? observacao? filters=trim
    timestamp created_at?=now
  }

  // O índice único (id_moto, versao_anterior) serializa transições concorrentes da mesma
  // moto: DISPONIVEL <-> RESERVADA tem ciclos, então a versão (e não o status anterior)
  // identifica cada transição. A segunda transição concorrente desfaz a transação inteira.
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_moto"}]}

    {
      type : "btree|unique"
      field: [{name: "id_moto"}, {name: "versao_anterior"}]
    }
    {
      type : "btree"
      field: [{name: "created_at", op: "desc"}]
    }
  ]
  guid = "w0eMxcQuohvq7zRSnH_sNyPF3kQ"
}
