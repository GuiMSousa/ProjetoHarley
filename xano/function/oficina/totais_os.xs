// Soma os itens da OS por tipo. Os itens são a fonte de verdade dos valores:
// as mutações gravam o resultado na OS (para a lista) e o detalhe o recalcula.
// Itens legados sem tipo contam como PECA.
function "Oficina/totais_os" {
  input {
    int os_id
  }

  stack {
    db.query itens_ordem_servico {
      where = $db.itens_ordem_servico.id_os == $input.os_id
      output = ["id", "tipo_item", "valor_total_item"]
      return = {type: "list"}
    } as $itens

    var $valor_pecas {
      value = 0
    }

    var $valor_servicos {
      value = 0
    }

    foreach ($itens) {
      each as $item {
        conditional {
          if ($item.tipo_item == "SERVICO") {
            var.update $valor_servicos {
              value = $valor_servicos + ($item.valor_total_item ?? 0)
            }
          }
          else {
            var.update $valor_pecas {
              value = $valor_pecas + ($item.valor_total_item ?? 0)
            }
          }
        }
      }
    }

    var $totais {
      value = {
        valor_pecas   : $valor_pecas|round:2
        valor_servicos: $valor_servicos|round:2
        valor_total   : ($valor_pecas + $valor_servicos)|round:2
      }
    }
  }

  response = $totais
  guid = "si4Wb2ELhkVmI2WQnmjKgXiLYmU"
}
