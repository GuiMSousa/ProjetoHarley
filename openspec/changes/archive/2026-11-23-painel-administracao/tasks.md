# Tarefas

Ordem de execução: 0 → 1 → 2 → 3 → 4 → 5 → 6. Cada bloco termina com a suíte offline passando (`ruff`, `compileall`, `reflex compile --dry`, `pytest -m "not integration and not browser"`).

## 0. Decisões e pré-requisitos

- [x] D1 a D9 fechadas pelo usuário em 2026-11-23 (`design.md`).
- [x] Salvaguardas S1 a S4 aprovadas pelo usuário em 2026-11-23 (`design.md` §3).
- [x] 0.2 Prova ao vivo do `PATCH` com payload parcial (2026-11-23: 1 login GERENTE, `POST funcionarios` e `PATCH funcionarios/5`).
  - Criou o "Funcionário Teste" (id 5, VENDEDOR, ativo), que fica para os testes de `/admin`.
  - O `PATCH` só com o `contato` respondeu 400 "Missing param: nome_funcionario", por causa do `dblink`.
  - Nada foi alterado. A correção é a D10 (bloco 1).
  - A primeira tentativa, no mesmo dia, parou antes de gravar, porque não havia cliente de teste.
- [x] Sintaxe confirmada no MCP `xano-developer` e na documentação local: `paging` com `totals`, os operadores nulos `==?`/`>=?`/`<=?`, `left join` em `user` a partir de `event_log` e `db.edit user` gravando `password`.

## 1. Backend Xano (local, sem push)

- [x] `api/harley/admin/usuarios_GET.xs`:
  - `enforce_role` `GERENTE` primeiro;
  - `db.query user` com `left join` em `funcionarios`;
  - linhas montadas com lista de campos permitidos, sem `password` e `password_reset`.
- [x] `api/harley/admin/usuarios_id_senha_POST.xs`:
  - `enforce_role` `GERENTE`;
  - pré-condições antes de gravar: alvo existe, não é o próprio gerente, não tem `role` `admin`, o funcionário dele não é `GERENTE` (revisão M1, com checagem de nulo) e a confirmação confere;
  - `db.edit user {password}`;
  - `log_event` `admin_reset_password` com `metadata` explícito;
  - resposta `{id, name, email}`.
- [x] `api/harley/admin/eventos_GET.xs`:
  - `enforce_role` `GERENTE`;
  - filtros opcionais de `action` e período (`data_inicio`/`data_fim`, até 366 dias, `400` se inválido);
  - `left join` em `user` e `funcionarios`;
  - `created_at` decrescente e `paging` de 25 com totais.
- [x] Nos três: campos de `db.get`/`single` lidos só depois da checagem de nulo; nenhuma expressão como argumento de filtro (`:(`).
- [x] D10: `dblink` deu lugar a entradas explícitas e opcionais nos `PATCH` de clientes, fornecedores, funcionários, motos de clientes e produtos.
- [x] Validar os `.xs` novos e alterados e o diretório `xano/` no MCP.

## 2. Contratos estáticos (`tests/`)

- [x] `test_admin_contracts.py`:
  - `enforce_role` `GERENTE` como primeiro passo dos três;
  - a lista de usuários sem `password` e montada com campos permitidos;
  - as pré-condições do reset antes do `db.edit`;
  - a resposta e o `metadata` do reset sem senha;
  - `paging` de 25 com totais, ordem decrescente e filtros nulos;
  - nenhum `:(`.
- [x] Contrato de parâmetros (`SystemRulesSyncTests`): cada valor de `PARAMETROS_SISTEMA` é igual ao do `.xs` que o aplica (reserva, balcão, entrada, resumo).
- [x] Contrato do `PATCH` parcial (`PartialPatchContractTests`): sem `dblink`, todos os campos opcionais, `pick` mantido e saldo do produto fora.
- [x] Mutações em memória: 19 regressões, e todas falham.

## 3. Reflex

- [x] `services/admin.py`: DTOs de leitura sem senha, `AcessoCreate`, `SenhaReset`, `EventosPagina`, `senha_problema` (política da tabela, sem `trim`) e `PARAMETROS_SISTEMA`.
- [x] `DIAS_RESERVA_MAXIMO` em `services/motos.py`, usada pela validação, pelo campo de `/vendas` e pela aba de parâmetros.
- [x] `XanoClient`: `list_usuarios_admin`, `criar_acesso` (grupo Authentication), `redefinir_senha`, `list_eventos(page, action, periodo)` e `reactivate_funcionario`.
- [x] `admin_state.py`:
  - `load_admin` guardado por `role_allows_route`;
  - abas e modais de criar acesso, redefinir senha e confirmar a mudança de status;
  - `yield` antes de cada chamada ao Xano;
  - senhas limpas ao fechar e após salvar;
  - S1 também no `confirm_status`.
- [x] `admin_pages.py`:
  - três abas com `rx.tabs`, `data_table`, `pager`, `labeled` e `modal_panel`;
  - todo `rx.select` dentro de `labeled`;
  - S1 a S4 na interface.
- [x] `admin_placeholder` trocado pela página nova e removido.
- [x] `tests/test_admin_state.py` (estado, regras de linha, política de senha e cliente com `MockTransport`) e os 3 handlers de fechamento no `RESETS` de `tests/test_modal_accessibility.py`.

## 4. Revisão

- [x] 1ª rodada (2026-11-23), 5 ciclos sem achado bloqueante. Os 5 achados foram corrigidos localmente:
  - M1: o reset recusa a conta de outro gerente no servidor, e a interface não oferece o botão;
  - L1: a paginação da auditoria checa o papel;
  - L2: até `lg`, cada usuário é uma célula empilhada, e as ações ficam visíveis sem rolagem lateral, medido em 320, 360, 600, 768, 1024 e 1280 px;
  - L5: o aviso das listas operacionais está na confirmação de desativação;
  - M2: entrou no bloco 5.
- [ ] Rodada de confirmação das correções (opcional): não executada. O usuário seguiu para a publicação, e a bateria ao vivo do bloco 5 cobriu os pontos corrigidos.

## 5. Publicação controlada (com OK do usuário)

- [x] `--dry-run` direcionado aos 3 `.xs` novos e aos 5 `PATCH` (2026-11-23): a prévia veio com 3 criados e 5 atualizados, e nada mais.
- [x] Push com o OK do usuário (`--force` só no push real, depois de a CLI pedir confirmação). O `--dry-run` seguinte respondeu "No changes to push", e os GUIDs dos 3 novos endpoints foram gravados nos arquivos.
- [x] Bateria ao vivo (2026-11-23, ~2,5 s entre chamadas), 8 de 8 aprovadas:
  - `GET admin/usuarios` respondeu 200, sem `password` e `password_reset`;
  - o `PATCH` parcial do `contato` do "Funcionário Teste" (id 5) respondeu 200, e só o contato mudou;
  - M2: `{"ativo": false}` e `{"ativo": true}` responderam 200, e só o `ativo` mudou; o `false` sobrevive aos filtros;
  - `auth/signup` criou o usuário de teste 5, e `POST admin/usuarios/5/senha` respondeu 200 sem a senha;
  - `GET admin/eventos` respondeu 200, com `itemsTotal` e `pageTotal` e o `admin_reset_password` só com ids;
  - o VENDEDOR recebeu 403 nos três endpoints, com o reset apontado para o usuário de teste;
  - ao final, o "Funcionário Teste" ficou inativo e com o contato original.

## 6. Documentação e arquivamento

- [x] Atualizados:
  - `docs/xano-api-client.md`, com a seção Administração, a matriz de acesso, o `PATCH` parcial e a lição do `dblink`;
  - `docs/domain-model.md`, com o reset pelo gerente, a revogação e as ações auditadas;
  - `docs/quality.md`, com a bateria ao vivo e o débito do "Desativar" encerrado.
- [x] Arquivada em 2026-11-23: `openspec/specs/administracao.md` criada e o delta de `arquitetura-e-contratos.md` aplicado.
