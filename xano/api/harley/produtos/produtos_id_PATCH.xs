// Edita um produto (GERENTE). PATCH parcial: só os campos declarados e enviados são gravados.
// Campos opcionais e explícitos: com `dblink`, {"ativo": false} sozinho (Desativar) respondia 400
// "Missing param", porque o Xano exigia os campos obrigatórios da tabela (2026-11-23). O saldo
// (estoque_qtd e versao_estoque) não é declarado e ainda sai do payload: só o livro de estoque o muda.
query "produtos/{produtos_id}" verb=PATCH {
  api_group = "HARLEY"
  auth = "user"

  input {
    int produtos_id? filters=min:1
    text? codigo? filters=trim
    text? nome_produto? filters=trim
    text? descricao? filters=trim
    text? categoria? filters=trim
    decimal? preco_venda? filters=min:0.01
    bool? ativo?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check
      util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch produtos {
      field_name = "id"
      field_value = $input.produtos_id
      data = `$input|pick:($raw_input|keys)`|unset:"estoque_qtd"|unset:"versao_estoque"|filter_null|filter_empty_text
    } as $model
  }

  response = $model
  guid = "sk8RGWwKFKvwhCb1GNoJO598Qc4"
}