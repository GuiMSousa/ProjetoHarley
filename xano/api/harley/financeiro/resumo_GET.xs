// Visão consolidada de receitas e despesas por período (Change 10). Dados financeiros: somente
// GERENTE. O Reflex envia os limites do dia (00:00 e 23:59:59.999, UTC-3) em milissegundos.
query "financeiro/resumo" verb=GET {
  api_group = "HARLEY"
  auth = "user"

  input {
    timestamp inicio
    timestamp fim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "GERENTE"}
    } as $role_check

    function.run "Financeiro/resumo_operacoes" {
      input = {inicio: $input.inicio, fim: $input.fim}
    } as $resumo
  }

  response = $resumo
  guid = "QmgPOkroWZovK6mXNQB_cPGFV7g"
}
