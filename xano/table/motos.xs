// Unidades físicas de motos no estoque da loja (Change 8).
// O status muda somente por Vendas/transicionar_moto (reserva e cancelamento).
table motos {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }

    // Cliente da reserva (e da venda, na Change 9).
    int clientes_id? {
      table = "clientes"
    }

    // Legado, somente leitura.
    text marca? filters=trim
    text modelo? filters=trim

    // Campos da Change 8: anuláveis para preservar unidades anteriores.
    int? id_modelo? {
      table = "modelos_moto"
    }

    // VIN de 17 caracteres, normalizado em caixa alta; único também contra motos_clientes.
    text? chassi? filters=trim|upper

    // Nome de uma das variacoes_cor do modelo.
    text? cor? filters=trim

    int? ano_modelo? filters=min:1990
    decimal? preco_venda? filters=min:0.01

    enum? status?=DISPONIVEL {
      values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]
    }

    // Vendedor da reserva, derivado do usuário autenticado.
    int? id_vendedor_reserva? {
      table = "funcionarios"
    }

    timestamp? reservada_ate?

    // Incrementada a cada transição; nulo equivale a 0.
    int? versao_status? filters=min:0

    timestamp? atualizado_em?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "clientes_id", op: "desc"}]}
    {type: "btree|unique", field: [{name: "chassi"}]}
    {type: "btree", field: [{name: "id_modelo"}]}
    {type: "btree", field: [{name: "status"}]}
  ]
  guid = "7HTEhAwc3Lhjg19mElJ3FM0Rcdo"
}
