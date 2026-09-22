// Add ITEM record
query item verb=POST {
  api_group = "Crud"

  input {
    dblink {
      table = "ITEM"
    }
  }

  stack {
    db.add ITEM {
      enforce_hidden_fields = false
      data = {
        created_at    : "now"
        pedido_id     : $input.pedido_id
        qtd           : $input.qtd
        valor_unit    : $input.valor_unit
        subtotal      : $input.subtotal
        produto_id    : $input.produto_id
        status_item_id: $input.status_item_id
      }
    } as $model
  }

  response = $model
  guid = "NRlQ-niZjLlWNUzUoJXD9lN928Q"
}