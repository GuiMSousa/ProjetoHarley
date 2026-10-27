// Detalhe interno de uma unidade do estoque: modelo, cliente e vendedor da reserva e a linha
// do tempo de status. Reutilizado pelo GET, pelo cadastro, pela edição e pelas reservas.
function "Vendas/detalhe_moto" {
  input {
    int moto_id
  }

  stack {
    db.get motos {
      field_name = "id"
      field_value = $input.moto_id
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

    db.get modelos_moto {
      field_name = "id"
      field_value = $moto.id_modelo
      output = ["id", "nome_modelo", "familia", "variacoes_cor", "imagem_principal", "galeria"]
    } as $modelo

    db.get clientes {
      field_name = "id"
      field_value = $moto.clientes_id
      output = ["id", "nome_cliente"]
    } as $cliente

    db.get funcionarios {
      field_name = "id"
      field_value = $moto.id_vendedor_reserva
      output = ["id", "nome_funcionario"]
    } as $vendedor

    db.query historico_status_moto {
      join = {
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.historico_status_moto.id_funcionario == $db.funcionarios.id
        }
      }

      where = $db.historico_status_moto.id_moto == $input.moto_id
      eval = {
        nome_funcionario: $db.funcionarios.nome_funcionario
      }

      sort = {id: "asc"}
      return = {type: "list"}
    } as $historico

    // galeria: != "private" (e não == "public") mantém fotos públicas legadas sem o atributo access.
    var $detalhe {
      value = $moto
        |set:"nome_modelo":$modelo.nome_modelo
        |set:"familia":$modelo.familia
        |set:"variacoes_cor":$modelo.variacoes_cor
        |set:"imagem_principal":$modelo.imagem_principal
        |set:"galeria":((($modelo.galeria ?? [])|filter:$$.access != "private")|map:$$.path)
        |set:"nome_cliente":$cliente.nome_cliente
        |set:"nome_vendedor":$vendedor.nome_funcionario
        |set:"historico":$historico
    }
  }

  response = $detalhe
  guid = "gLkGCOaybq2Pv1AYt5hAybC8REI"
}
