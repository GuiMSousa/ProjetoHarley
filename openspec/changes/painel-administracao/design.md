# Design: painel de administração `/admin` (Change 18)

> **Situação:** proposta, 2026-11-23. As decisões D1 a D9 foram fechadas pelo usuário; as salvaguardas S1 a S4 são recomendações desta proposta e precisam de aprovação no Apply.

## 1. O que já existe e é reutilizado

| Necessidade | Reutiliza | Observação |
| --- | --- | --- |
| Rota e proteção | `/admin` em `ROUTE_ROLES` (`GERENTE`), `guarded_page` | Só troca o conteúdo do placeholder. |
| Lista de funcionários sem conta | `GET funcionarios` (`GERENTE`) | O Reflex cruza com os `id_funcionario` de `GET admin/usuarios`. |
| Criar acesso | `POST auth/signup` (grupo Authentication) | Já exige funcionário ativo sem conta e email único, e já registra `signup`. Responde `{user_id, id_funcionario}`, sem token. |
| Desativar acesso | `PATCH funcionarios/{id}` com `ativo = false` | `enforce_role` nega toda operação a funcionário inativo; o login do Reflex recusa a sessão. |
| Componentes | `modal_panel`, `modal_header`, `labeled`, `data_table`, `toolbar`, `pager`, `error_callout`, `primary_button` | Seguem `design-system.md`, cobertos pelos testes de modal, de `rx.select` e de campos. |

## 2. Decisões

**D1. Escopo:** três abas em `/admin`, somente para `GERENTE`: Usuários e acessos, Auditoria de acessos, Parâmetros do sistema.

**D2. `GET admin/usuarios`** (grupo HARLEY):
- o primeiro passo é `enforce_role` `GERENTE`;
- uma única `db.query user`, com `left join` em `funcionarios`, sem N+1;
- a saída tem `id`, `name`, `email`, `role`, `created_at`, `id_funcionario`, `nome_funcionario`, `tipo`, `cargo` e `ativo`;
- `password` e `password_reset` NUNCA saem;
- usuário sem funcionário, criado pelo painel, sai com os campos do funcionário nulos: o `left join` não quebra.

**D3. Criar acesso:**
- o modal lista só os funcionários ativos sem conta;
- pede email, senha e confirmação;
- o Reflex valida a política da tabela `user`: mínimo de 8 caracteres, com ao menos uma letra e um número, e sem `trim`;
- chama `auth/signup` sem alterá-lo.

**D4. Desativar acesso:**
- usa `PATCH funcionarios/{id}` com `{"ativo": false}` e um diálogo de confirmação;
- a reativação usa o mesmo `PATCH` com `{"ativo": true}`.

**D5. `POST admin/usuarios/{id}/senha`** (grupo HARLEY, `GERENTE`):
- entrada: `password` e `confirm_password`, com a política da tabela e sem `trim`;
- pré-condições, todas antes de gravar:
  - o usuário alvo existe (404);
  - o alvo não é o próprio gerente (400 "Para trocar a sua senha, use a troca de senha do próprio usuário."), porque a troca da própria senha exige a senha atual;
  - o alvo tem `role` `member` (403), porque redefinir a senha de um usuário `admin` daria a quem a define um acesso que passa por qualquer papel;
  - a confirmação confere (400);
- grava com `db.edit user {password: …}`: o campo `password` é armazenado como hash;
- registra `log_event` com `action: "admin_reset_password"` e `metadata` explícito (`id_usuario`, `id_funcionario`, `id_gerente`), sem senha, hash nem token;
- responde `{id, name, email}`, sem a senha.

**D6. `GET admin/eventos`** (grupo HARLEY, `GERENTE`):
- entradas: `page` (padrão 1, mínimo 1), `action` (opcional), `inicio` e `fim` (opcionais, em milissegundos; período de até 366 dias, como no resumo financeiro);
- uma `db.query event_log` com `left join` em `user` e em `funcionarios`, ordenada por `created_at` decrescente;
- `return = {type: "list", paging: {page: $input.page, per_page: 25, totals: true}}`, a sintaxe documentada;
- a saída tem `id`, `created_at`, `action`, `user_id`, `nome_usuario`, `nome_funcionario` e `metadata`;
- as ações registradas hoje são `login`, `signup`, `reset_password` e `welcome_email_sent`; esta change acrescenta `admin_reset_password`.

**D7. Parâmetros:**
- a aba lê as constantes que o Reflex já usa: `DIAS_RESERVA_PADRAO`, o máximo de 30 dias da reserva, `MAX_ITENS_VENDA`, `MAX_ITENS_ENTRADA`, `PERIODO_MAXIMO_DIAS` e `OPERACOES_LIMITE`;
- não cria endpoint nem tabela;
- um contrato estático confere que cada constante é igual ao valor no `.xs` correspondente, para que o painel nunca mostre uma regra diferente da que o servidor aplica.

**D8. Reflex:**
- `services/admin.py` com os DTOs, sem campo de senha na leitura;
- métodos novos no `XanoClient`; `criar_acesso` usa `_auth_base_url`, como o `login`;
- `admin_state.py`, cujo `on_load` restaura a sessão e só chama o Xano se `role_allows_route(role, "/admin")`;
- `admin_pages.py`, com `rx.tabs`;
- o placeholder sai de `dashboard_pages.py`.

**D9. Mensagens:** erros do Xano passam pelo tratamento existente (`_xano_error_response`), e todo envio troca o rótulo por um texto de progresso terminado em "…" (spec `design-system`, estados de carregamento).

## 3. Salvaguardas propostas (aprovar no Apply)

- **S1. Não se desativar:** o painel esconde "Desativar acesso" na linha do próprio gerente. O `PATCH funcionarios` não muda; quem quiser contornar pelo cadastro ainda consegue, e o painel do Xano recupera o acesso.
- **S2. Último gerente:** o painel avisa antes de desativar o último `GERENTE` ativo. O bloqueio no servidor exigiria mudar `PATCH funcionarios` e fica como débito.
- **S3. JWT emitido:** redefinir a senha não invalida a sessão aberta do alvo; o corte imediato é desativar o acesso. A aba deve dizer isso em uma linha.
- **S4. Senha temporária:** o gerente a informa ao funcionário fora do sistema. O sistema não envia a senha por email, porque o `welcome_email` não deve carregar segredos.

## 4. Riscos

| Risco | Mitigação |
| --- | --- |
| `pick:($raw_input\|keys)` do `PATCH` nunca provado ao vivo | Tarefa 0.2: prova controlada com um registro de teste, antes da publicação. |
| Paginação no servidor nunca usada neste projeto | Validar no MCP; contrato da sintaxe documentada; primeira leitura ao vivo confere `items` e os totais. |
| Leitura de registro `null` (lição de `detalhe_os`) | Campos de `db.get`/`single` só dentro de `if ($x != null)`; contrato estático. |
| Expressão como caminho de `get`/`set` (lição de `entrada_mercadoria`) | Proibida nos `.xs` novos; contrato `assertNotIn(":(")`. |
| `--dry-run` sem prévia segue para a confirmação | Nunca usar `--force` com `--dry-run`; parar se a prévia falhar (`docs/xano-api-client.md`). |
