// Detalhe interno de uma unidade do estoque: modelo, cliente e vendedor da reserva e a linha
// do tempo de status. Reutilizado pelo GET, pelo cadastro, pela edição e pelas reservas.
function "Vendas/detalhe_moto" {
  input {
    int moto_id
  }

  stack {
    // Joins à esquerda: uma unidade sem reserva (ou sem modelo) não tem esses ids, e um db.get
    // com field_value nulo respondia 400 "Missing param: field_value" (auditoria de 2026-10-27).
    db.query motos {
      join = {
        modelos_moto: {
          table: "modelos_moto"
          type : "left"
          where: $db.motos.id_modelo == $db.modelos_moto.id
        }
        clientes: {
          table: "clientes"
          type : "left"
          where: $db.motos.clientes_id == $db.clientes.id
        }
        funcionarios: {
          table: "funcionarios"
          type : "left"
          where: $db.motos.id_vendedor_reserva == $db.funcionarios.id
        }
      }

      where = $db.motos.id == $input.moto_id
      eval = {
        nome_modelo     : $db.modelos_moto.nome_modelo
        familia         : $db.modelos_moto.familia
        variacoes_cor   : $db.modelos_moto.variacoes_cor
        imagem_principal: $db.modelos_moto.imagem_principal
        galeria         : $db.modelos_moto.galeria
        nome_cliente    : $db.clientes.nome_cliente
        nome_vendedor   : $db.funcionarios.nome_funcionario
      }

      return = {type: "single"}
    } as $moto

    precondition ($moto != null) {
      error_type = "notfound"
      error = "Moto não encontrada."
    }

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
        |set:"galeria":((($moto.galeria ?? [])|filter:$$.access != "private")|map:$$.path)
        |set:"historico":$historico
    }
  }

  response = $detalhe
  guid = "gLkGCOaybq2Pv1AYt5hAybC8REI"
}
