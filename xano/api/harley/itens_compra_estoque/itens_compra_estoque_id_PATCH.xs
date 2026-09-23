// Edit itens_compra_estoque record
query "itens_compra_estoque/{itens_compra_estoque_id}" verb=PATCH {
  api_group = "HARLEY"

  input {
    int itens_compra_estoque_id? filters=min:1
    dblink {
      table = "itens_compra_estoque"
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch itens_compra_estoque {
      field_name = "id"
      field_value = $input.itens_compra_estoque_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "3oWtgJ2Yb2cev-jWQNQYGOhuKHc"
}