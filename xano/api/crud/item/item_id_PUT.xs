// Update ITEM record
query "item/{item_id}" verb=PUT {
  api_group = "Crud"

  input {
    int item_id? filters=min:1
    dblink {
      table = "ITEM"
    }
  }

  stack {
    db.edit ITEM {
      field_name = "id"
      field_value = $input.item_id
      enforce_hidden_fields = false
      data = {
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
  guid = "suENl6kDl9pSfXq6NHrlB-wNxmI"
}