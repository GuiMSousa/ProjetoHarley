# Tarefas

Ordem de execução: 0 → 1 → 2 → 3 → 4 → 5 → 6. Cada bloco termina com a suíte offline passando (`ruff`, `compileall`, `reflex compile --dry`, `pytest -m "not integration and not browser"`).

## 0. Decisões e pré-requisitos

- [x] D1 a D9 fechadas pelo usuário em 2026-11-23 (`design.md`).
- [ ] Aprovar as salvaguardas S1 a S4 (`design.md` §3).
- [ ] 0.2 Provar ao vivo o `PATCH` com payload parcial (`pick:($raw_input|keys)`): alterar e restaurar um campo não destrutivo de um registro **de teste**, com autorização. A tentativa de 2026-11-23 parou antes de gravar, porque produção tinha um único cliente e ele não é de teste. É preciso um registro de teste, ou a autorização para usar um registro real, antes da publicação (tarefa 5).
- [ ] No MCP `xano-developer`, confirmar a sintaxe de `paging` com `totals`, de `left join` em `user` a partir de `event_log` e de `db.edit user` gravando o campo `password`.

## 1. Backend Xano (local, sem push)

- [ ] `api/harley/admin/usuarios_GET.xs`: `enforce_role` `GERENTE` primeiro; `db.query user` com `left join` em `funcionarios`; saída sem `password` e `password_reset`.
- [ ] `api/harley/admin/usuarios_id_senha_POST.xs`: `enforce_role` `GERENTE`; pré-condições antes de gravar (alvo existe, não é o próprio gerente, `role` `member`, confirmação confere); `db.edit user {password}`; `log_event` `admin_reset_password` com `metadata` explícito; resposta `{id, name, email}`.
- [ ] `api/harley/admin/eventos_GET.xs`: `enforce_role` `GERENTE`; filtros opcionais de `action` e período (até 366 dias, `400` se inválido); `left join` em `user` e `funcionarios`; `created_at` decrescente; `paging` de 25 com totais.
- [ ] Nos três: campos de `db.get`/`single` lidos só dentro de `if ($x != null)`; nenhuma expressão como argumento de filtro (`:(`).
- [ ] Validar os três `.xs` e o diretório `xano/` no MCP.

## 2. Contratos estáticos (`tests/`)

- [ ] `test_admin_contracts.py`:
  - `enforce_role` `GERENTE` como primeiro passo dos três;
  - `password` e `password_reset` fora da saída de `admin/usuarios`;
  - as pré-condições do reset vêm antes do `db.edit`;
  - a resposta do reset não tem senha;
  - o `metadata` do `log_event` é explícito e sem senha;
  - `paging` de 25 com totais;
  - nenhum `:(`.
- [ ] Contrato de parâmetros: cada constante do Reflex (`DIAS_RESERVA_PADRAO`, máximo da reserva, `MAX_ITENS_VENDA`, `MAX_ITENS_ENTRADA`, `PERIODO_MAXIMO_DIAS`, `OPERACOES_LIMITE`) igual ao valor do `.xs` que a aplica.
- [ ] Mutações em memória para cada contrato novo: o arquivo correto passa, e cada regressão falha.

## 3. Reflex

- [ ] `services/admin.py`:
  - DTOs de leitura sem senha;
  - `AcessoCreate`, com a política de senha da tabela, sem `trim` e com confirmação;
  - `SenhaReset`.
- [ ] `XanoClient`: `list_usuarios_admin`, `criar_acesso` (grupo Authentication), `redefinir_senha` e `list_eventos(page, action, periodo)`.
- [ ] `admin_state.py`: `load_admin` guardado por `role_allows_route`; abas; modais de criar acesso, redefinir senha e confirmar desativação; `yield` antes de cada chamada ao Xano; mensagens de erro pelo tratamento existente.
- [ ] `admin_pages.py`:
  - três abas com `rx.tabs`, `data_table`, `toolbar`, `pager` e `modal_panel`;
  - todo `rx.select` dentro de `labeled` ou com `custom_attrs`;
  - "Desativar acesso" fora da linha do próprio gerente (S1);
  - aviso de sessão aberta (S3).
- [ ] Trocar `admin_placeholder` pela página nova e remover o placeholder.
- [ ] Testes de estado e de DTO; acrescentar os handlers de fechamento dos modais novos ao `RESETS` de `tests/test_modal_accessibility.py`.

## 4. Revisão

- [ ] De 4 a 5 ciclos de revisão (RBAC, segredos, nulos, paginação e UI), com mutações e as medidas de 320, 360 e 1280 px nas páginas de dados fictícios.

## 5. Publicação controlada (com OK do usuário)

- [ ] Tarefa 0.2 concluída.
- [ ] `--dry-run` direcionado a cada `.xs` novo. Parar se a prévia não vier, e nunca usar `--force` com `--dry-run`.
- [ ] Push com o OK do usuário e `--dry-run` seguinte com "No changes to push".
- [ ] Ao vivo, com autorização:
  - 1 login `GERENTE` com leitura de `admin/usuarios` e `admin/eventos`;
  - 1 login `VENDEDOR` recebendo `403` nos três endpoints;
  - um reset de senha num usuário **de teste**.

## 6. Documentação e arquivamento

- [ ] Atualizar:
  - `docs/xano-api-client.md`, com os endpoints e a matriz de acesso;
  - `docs/domain-model.md`, com o reset pelo gerente;
  - `docs/quality.md`.
- [ ] Arquivar a change, criando `openspec/specs/administracao.md` e aplicando o delta de `arquitetura-e-contratos.md`.
