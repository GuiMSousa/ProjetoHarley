// Trilha de auditoria das transições de status das ordens de serviço (somente inserção).
table historico_status_os {
  auth = false

  schema {
    int id
    int id_os {
      table = "ordens_servico"
    }

    // Nulo na abertura da OS.
    enum? status_anterior? {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    enum status_novo {
      values = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
    }

    // Funcionário autenticado que executou a transição.
    int id_funcionario {
      table = "funcionarios"
    }

    timestamp created_at?=now
    text? observacao? filters=trim
  }

  // O índice único (id_os, status_anterior) garante que cada OS saia de cada status uma
  // única vez (a máquina de estados não tem ciclos) e serializa transições concorrentes.
  // A linha de abertura tem status_anterior nulo e não colide.
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_os"}]}

    {
      type : "btree|unique"
      field: [{name: "id_os"}, {name: "status_anterior"}]
    }
    {
      type : "btree"
      field: [{name: "created_at", op: "desc"}]
    }
  ]
  guid = "k2NRShlrMyvKtFmsmjkC03NrtQs"
}
