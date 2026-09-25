// Detalhe da OS com linha do tempo de status, itens (leitura) e dados enriquecidos.
query "ordens_servico/{ordens_servico_id}" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    int ordens_servico_id filters=min:1
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "ALL"}
    } as $role_check

    function.run "Oficina/detalhe_os" {
      input = {os_id: $input.ordens_servico_id}
    } as $model
  }

  response = $model
  guid = "VHi9aYRau7iZIUwKirqWkA4z2xg"
}
