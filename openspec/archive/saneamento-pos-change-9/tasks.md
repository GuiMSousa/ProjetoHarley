# Tarefas

## 1. Skills

- [x] Conferir as quatro skills instaladas (`frontend-design`, `web-design-guidelines`, `python-testing-patterns`, `playwright-best-practices`): `SKILL.md` válido e registro em `~/.agents/.skill-lock.json`.
- [x] Ligar as quatro skills ao Claude Code (`npx skills add … -g --agent claude-code --copy`); antes estavam ligadas só a AiderDesk, Antigravity, Gemini CLI e GitHub Copilot.

## 2. Segurança e RBAC (Xano)

- [x] Inventariar os 86 endpoints: `auth`, papel exigido, bloqueio, IDs de funcionário vindos do payload e escritas.
- [x] Confirmar a validação no servidor de `id_mecanico` (OS) e `id_funcionario` (`auth/signup`).
- [x] `transacoes`: leitura, `POST`, `PUT` e `PATCH` só para `GERENTE`; `PUT` preserva o autor; mensagem do `DELETE` atualizada.
- [x] `logs/user/my_events`: `enforce_role` `ALL`.
- [x] Manter `auth/me` sem `enforce_role` (só identidade) e a vitrine pública (Change 8, D3).
- [x] Registrar a pendência do token do Swagger (ação no workspace).

## 3. Integridade (Xano)

- [x] Conferir que `Vendas/transicionar_moto` e `Estoque/movimentar_estoque` só são chamadas dentro de `db.transaction` (7 chamadas), com versão e índice único.
- [x] Registrar que `Oficina/detalhe_os` é só leitura e que a transição da OS é atômica no `POST ordens_servico/{id}/status`.
- [x] `entrada_mercadoria` POST: validações antes da transação e `try_catch` com mensagem de conflito.
- [x] Confirmar que não há arquivos temporários ou duplicados em `xano/` e manter as rotas antigas bloqueadas (o push parcial não remove objetos).
- [x] Validador XanoScript (123 arquivos) e `--dry-run`.

## 4. Frontend (Reflex)

- [x] Logo: máximo de 45 px, caixa reservada, `alt` como fallback, `fetchPriority` alto e `translate="no"`.
- [x] Tema: `color-scheme: dark`, `theme-color`, `prefers-reduced-motion`, `tabular-nums`, `touch-action` e pares `#121212` no teste de contraste.
- [x] Carregamento: `yield` depois de ligar a flag em 22 handlers (login, cadastros, entradas, catálogo, vendas e oficina).
- [x] Acessibilidade:
  - `labeled` como `<label>`;
  - `aria-label`, `type="search"` e `autocomplete` na busca e no login;
  - skip link e `<main>`;
  - modal com `role="dialog"`, `aria-modal` e `overscroll-behavior`;
  - alertas e status anunciados;
  - ícones decorativos ocultos;
  - "…" nos textos.
- [x] Responsividade a 500 px e 1440 px com Playwright (rotas temporárias removidas ao final).

## 5. Testes

- [x] pytest 9.1.1 em `requirements-dev.txt`; `pytest.ini` com `testpaths`, `-ra` e marcadores estritos.
- [x] `tests/__init__.py`, `tests/conftest.py` (marcadores `integration`, `writes`, `concurrency`) e `tests/event_runner.py` (`run_event`).
- [x] Integração opt-in (`XANO_TEST_ALLOW_WRITES` ou `XANO_TEST_LIVE`), ignorada com motivo por padrão.
- [x] Testes novos de RBAC, transações, entrada, funções versionadas, carregamento, logo, skip link e tema.
- [x] `python -m pytest` e `python -m unittest discover -s tests` verdes.

## 6. Documentação e specs

- [x] `openspec/specs/cadastros.md` (Change 3 não tinha spec).
- [x] `arquitetura-e-contratos.md`: requisito de `POST motos` atualizado; RBAC em todo endpoint; dados financeiros; autoria nas correções.
- [x] `estoque-entradas.md`: corrida da entrada.
- [x] `design-system.md`: responsividade em 500 px, estados de carregamento e acessibilidade.
- [x] Docs: `xano-api-client.md` (checklist, matriz, entradas, testes), `domain-model.md`, `project-structure.md`, anexo da auditoria.
- [x] Change 10: proposta, design e tarefas alinhados ao que o saneamento já aplicou.

## Fora do repositório (usuário)

- [ ] `xano workspace push -d ./xano`.
- [ ] Desligar o Swagger público ou exigir token no workspace.
- [ ] Integração com credenciais `XANO_TEST_*` (`XANO_TEST_LIVE=true` e depois `XANO_TEST_ALLOW_WRITES=true`).
