// Delete itens_compra_estoque record
query "itens_compra_estoque/{itens_compra_estoque_id}" verb=DELETE {
  api_group = "HARLEY"
  auth = "user"

  input {
    int itens_compra_estoque_id? filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      db.del itens_compra_estoque {
      field_name = "id"
      field_value = $input.itens_compra_estoque_id
    }
  }

  response = null
  guid = "BHOcUi_dduF_gF8sLfgb2nCqQQ8"
}