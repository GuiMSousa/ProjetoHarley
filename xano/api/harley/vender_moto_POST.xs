// Venda de uma moto do estoque (GERENTE ou VENDEDOR). A lógica atômica fica em
// Vendas/vender_moto; o funcionário vem do usuário autenticado ($auth.id -> user.id_funcionario),
// nunca do payload.
query vender_moto verb=POST {
  api_group = "HARLEY"
  auth = "user"

  input {
    int id_moto filters=min:1
    int id_cliente filters=min:1
    text placa filters=trim|upper
    decimal valor_venda filters=min:0.01
    text? observacao? filters=trim|max:500
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "VENDEDOR"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id_funcionario"]
    } as $auth_user

    precondition ($auth_user.id_funcionario != null) {
      error_type = "accessdenied"
      error = "Seu usuário não está vinculado a um funcionário."
    }

    function.run "Vendas/vender_moto" {
      input = {
        id_moto       : $input.id_moto
        id_cliente    : $input.id_cliente
        id_funcionario: $auth_user.id_funcionario
        placa         : $input.placa
        valor_venda   : $input.valor_venda
        observacao    : $input.observacao
      }
    } as $resultado
  }

  response = $resultado
  guid = "TXVsxPKXswNv2oAFbxnkhUZcz1E"
}
