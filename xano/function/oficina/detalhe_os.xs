// Monta o detalhe de uma OS: dados enriquecidos, linha do tempo de status, itens e totais.
// Os totais são recalculados a partir dos itens (fonte de verdade), o que cobre OS legadas.
function "Oficina/detalhe_os" {
  input {
    int os_id
  }

  stack {
    db.get ordens_servico {
      field_name = "id"
      field_value = $input.os_id
    } as $os

    precondition ($os != null) {
      error_type = "notfound"
      error = "Ordem de serviço não encontrada."
    }

    db.get motos_clientes {
      field_name = "id"
      field_value = $os.id_moto_cliente
      output = ["id", "id_cliente", "modelo", "placa"]
    } as $moto

    var $id_cliente {
      value = $os.id_cliente ?? $moto.id_cliente
    }

    db.get clientes {
      field_name = "id"
      field_value = $id_cliente
      output = ["id", "nome_cliente"]
    } as $cliente

    db.get funcionarios {
      field_name = "id"
      field_value = $os.id_funcionario
      output = ["id", "nome_funcionario"]
    } as $autor

    db.get funcionarios {
      field_name = "id"
      field_value = $os.id_mecanico
      output = ["id", "nome_funcionario"]
    } as $mecanico

    db.query historico_status_os {
      join = {
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.historico_status_os.id_funcionario == $db.funcionarios.id
        }
      }

      where = $db.historico_status_os.id_os == $input.os_id
      eval = {
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $historico

    db.query itens_ordem_servico {
      join = {
        produtos: {
          table: "produtos"
          type : "left"
          where: $db.itens_ordem_servico.id_produto == $db.produtos.id
        }
      }

      where = $db.itens_ordem_servico.id_os == $input.os_id
      eval = {
        codigo      : $db.produtos.codigo
        nome_produto: $db.produtos.nome_produto
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $itens

    function.run "Oficina/totais_os" {
      input = {os_id: $input.os_id}
    } as $totais

    var $detalhe {
      value = $os
        |set:"id_cliente":$id_cliente
        |set:"nome_cliente":$cliente.nome_cliente
        |set:"placa":$moto.placa
        |set:"modelo":$moto.modelo
        |set:"nome_funcionario":$autor.nome_funcionario
        |set:"nome_mecanico":$mecanico.nome_funcionario
        |set:"historico":$historico
        |set:"itens":$itens
        |set:"valor_pecas":$totais.valor_pecas
        |set:"valor_servicos":$totais.valor_servicos
        |set:"valor_total":$totais.valor_total
    }
  }

  response = $detalhe
  guid = "dndP0NUct7g4h2FCmDNAdtHRWqI"
}
