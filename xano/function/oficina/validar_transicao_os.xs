// Tabela única de transições de status das ordens de serviço.
//   ABERTA       -> EM_ANDAMENTO | CANCELADA
//   EM_ANDAMENTO -> CONCLUIDA    | CANCELADA
//   CONCLUIDA e CANCELADA são estados finais.
// CANCELADA exige observação (motivo do cancelamento).
function "Oficina/validar_transicao_os" {
  input {
    text status_atual
    text status_novo
    text? observacao?
  }

  stack {
    precondition ($input.status_atual != "CONCLUIDA" && $input.status_atual != "CANCELADA") {
      error_type = "inputerror"
      error = "OS encerrada não pode ser reaberta ou alterada."
    }

    var $permitida {
      value = ($input.status_atual == "ABERTA" && ($input.status_novo == "EM_ANDAMENTO" || $input.status_novo == "CANCELADA")) || ($input.status_atual == "EM_ANDAMENTO" && ($input.status_novo == "CONCLUIDA" || $input.status_novo == "CANCELADA"))
    }

    precondition ($permitida) {
      error_type = "inputerror"
      error = "Transição de status inválida: " ~ $input.status_atual ~ " → " ~ $input.status_novo ~ "."
    }

    var $motivo {
      value = ($input.observacao ?? "")|trim
    }

    precondition ($input.status_novo != "CANCELADA" || ($motivo|strlen) > 0) {
      error_type = "inputerror"
      error = "Informe o motivo do cancelamento."
    }
  }

  response = true
}
