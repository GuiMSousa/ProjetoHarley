# Proposta: painel de administração `/admin` (Change 18)

## Contexto

A rota `/admin` existe desde a Change 2, restrita ao `GERENTE` pela matriz `ROUTE_ROLES`, mas mostra só um aviso "em preparação" (`admin_placeholder`). A auditoria de 2026-11-23 mapeou o que já existe e o que falta:

- **Banco:** `user` (nome, email único, senha, `role` técnico, `id_funcionario`), `funcionarios` (nome, cargo, tipo, contato, `ativo`) e `event_log` (`user_id`, `action`, `metadata`, `created_at`, com índices por data e por usuário). Não existe tabela de parâmetros.
- **API:**
  - CRUD de `funcionarios` para o `GERENTE`, com `DELETE` em `403`;
  - `auth/signup`, só para o `GERENTE`: cria o usuário vinculado a um funcionário ativo sem conta, sem emitir token, e registra `signup` no `event_log`;
  - `reset/update_password`, só para a senha do próprio usuário e exigindo a senha atual;
  - `logs/user/my_events`, que lê só os eventos do próprio usuário.
- **Reflex:** `/cadastros/funcionarios` cuida dos dados do funcionário. O app não chama `signup`, `update_password` nem `my_events`.
- **Parâmetros:** as regras operacionais são constantes repetidas no Reflex e no Xano:

  | Regra | Valor |
  | --- | --- |
  | Prazo padrão da reserva | 7 dias |
  | Prazo máximo da reserva | 30 dias |
  | Itens por venda de balcão | até 30 |
  | Itens por entrada de mercadoria | até 50 |
  | Período do resumo financeiro | até 366 dias |
  | Operações listadas no resumo | até 500 |

## Problema

1. Dar acesso a um funcionário novo, ou redefinir a senha de quem a esqueceu, exige o painel do Xano. As recuperações por link estão desativadas desde a Change 2.
2. O gerente não vê quem entrou no sistema, nem quando.
3. As regras operacionais ficam espalhadas pelo código, sem um lugar onde o gerente as consulte.

## Objetivo

Entregar `/admin`, somente para o `GERENTE`, com três abas:

1. **Usuários e acessos:**
   - listar os usuários e o funcionário de cada um;
   - criar o acesso de um funcionário ativo sem conta;
   - desativar o acesso;
   - redefinir a senha de outro usuário.
2. **Auditoria de acessos:** ler o `event_log` paginado, com o nome do usuário e filtros por ação e período.
3. **Parâmetros do sistema:** mostrar as regras operacionais vigentes, só para leitura.

## Decisões fechadas

- **Listagem:** novo `GET admin/usuarios` (`GERENTE`). A resposta omite `password` e `password_reset`.
- **Criar acesso:** reutiliza `POST auth/signup`, sem alteração.
- **Desativar acesso:** reutiliza `PATCH funcionarios/{id}` com `ativo = false`, sem alteração. O `enforce_role` já corta o acesso no servidor, e o login do Reflex já recusa o funcionário inativo.
- **Redefinir senha:** novo `POST admin/usuarios/{id}/senha` (`GERENTE`). Grava a senha temporária, que o Xano guarda só como hash, registra `log_event` e nunca devolve a senha.
- **Auditoria:** novo `GET admin/eventos` (`GERENTE`), paginado no servidor, com `left join` para o nome do usuário e filtros por ação e período.
- **Parâmetros:** somente leitura, sem tabela nova e sem reabrir endpoints já validados ao vivo.

## Fora do escopo

- Tornar os parâmetros editáveis, o que exigiria tabela nova e mudar `reserva`, `balcao/vendas`, `entrada_mercadoria` e o resumo financeiro.
- Registrar no `event_log` as operações de negócio, como venda, OS e estoque, que já têm histórico próprio.
- Criar, editar ou excluir funcionários: isso continua em `/cadastros/funcionarios`.
- Alterar o `role` técnico (`admin`/`member`) ou criar usuários `admin`.
- Excluir usuários.
- Revogar o JWT já emitido. O corte imediato é a desativação do funcionário.
- Trocar a própria senha pela interface. O endpoint existe, mas a tela fica para outra change.
- Recuperação de acesso por email ou link.

## Pré-requisito em aberto

A desativação reutiliza `PATCH funcionarios/{id}`, cujo `pick:($raw_input|keys)` nunca rodou ao vivo, assim como o dos outros seis `PATCH` dos cadastros. A prova controlada de 2026-11-23 não pôde rodar: produção tinha um único cliente, que não é de teste. Ela continua obrigatória antes da publicação (tarefa 0.2).
