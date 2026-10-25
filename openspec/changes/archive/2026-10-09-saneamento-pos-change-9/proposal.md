# Proposta: saneamento pós-Change 9

## Contexto

Revisão geral pedida depois da Change 9: segurança e RBAC do Xano, integridade dos dados, UI/UX e acessibilidade do Reflex, testes com pytest e alinhamento das specs até a Change 9. A revisão aplicou as skills `web-design-guidelines` (regras de interface da Vercel), `frontend-design` (patamar de qualidade, sem trocar a identidade da marca), `python-testing-patterns` (pytest, marcadores, isolamento) e `playwright-best-practices` (verificação responsiva com viewport e localizadores por papel).

## Problemas tratados

1. **Transações financeiras abertas:** qualquer perfil lia todas as transações, e um `VENDEDOR` podia criar e alterar tipo, valor e data. O `PUT` substituía o autor original por quem editava.
2. **`logs/user/my_events` sem verificação de papel:** um token válido de funcionário desativado ainda lia os eventos.
3. **Entrada de mercadoria sem `try_catch`** (débito 6 da auditoria): uma corrida devolvia `500`, e a tela mostrava "Não foi possível comunicar com o Xano".
4. **Estados de carregamento invisíveis:** o Reflex só envia o estado ao fim do handler ou num `yield`. Como os handlers ligavam `is_saving` e chamavam o Xano sem `yield`, "Salvando…" nunca aparecia, o botão continuava habilitado durante o pedido e um segundo clique era enfileirado.
5. **Acessibilidade e tema:**
   - campos sem rótulo associado; busca e login só com placeholder; login sem `autocomplete`;
   - modais sem `role="dialog"`; erros não anunciados;
   - sem link para o conteúdo, sem `color-scheme: dark`, sem `prefers-reduced-motion` e sem `theme-color`;
   - logo sem limite máximo nem caixa reservada.
6. **Testes:** sem pytest. A integração real rodava sempre que o `.env` tinha a URL, dependendo de rede e do limite de `429`.
7. **Specs:** o requisito "criação de motocicleta de estoque" ainda descrevia o `POST motos` anterior à Change 8, e não havia spec dos cadastros (Change 3).

## Decisões

- **Transações:** leitura e lançamentos ou correções manuais só para `GERENTE`, com o autor preservado. A imutabilidade total (`403` para todos) continua sendo a decisão D5 da Change 10.
- **`auth/me` sem `enforce_role`:** devolve só a identidade de quem chama, e o Reflex precisa ler `funcionario.ativo` para explicar a desativação.
- **Rotas antigas não são apagadas:** o push parcial do Xano nunca remove objetos, e `--sync --delete` remove tudo o que faltar no local. As rotas antigas continuam bloqueadas com `403`, com rota e `guid` preservados.
- **Vitrine continua pública:** `catalogo` e `catalogo/{id}` são a superfície pública aprovada na Change 8 (D3), por isso continuam sem `auth`.
- **Token do Swagger:** o export guarda o token em texto puro, por isso não se corrige pelo arquivo. A ação é desligar o Swagger ou exigir token no workspace (usuário).
- **Integração opt-in:** só roda com `XANO_TEST_ALLOW_WRITES=true` (completa) ou `XANO_TEST_LIVE=true` (leitura). Fica marcada como `integration`, `writes` e `concurrency`.
- **Carregamento:** os handlers de submissão e de carga fazem `yield` logo depois de ligar a flag, seguindo o padrão da documentação do Reflex. Os testes usam `run_event`.

## Fora do escopo

- Lançamento financeiro da OS, imutabilidade total das transações e visão consolidada (Change 10).
- Dados pessoais de clientes visíveis ao mecânico (depende de decisão de negócio).
- Corrida residual de "uma OS em aberto por moto", de baixa probabilidade: exige uma trava no esquema.
- Tabelas em formato de cartões no celular. Hoje rolam dentro do card e, em `/vendas`, as ações exigem rolagem horizontal.

## Resultado aplicado

**Xano (8 endpoints):**
- `transacoes` GET, POST e `{id}` GET/PUT/PATCH exigem `GERENTE`; o PUT preserva o autor e a mensagem do DELETE foi atualizada.
- `entrada_mercadoria` POST passou a ter as validações antes da transação e um `try_catch` com mensagem de conflito.
- `logs/user/my_events` passou a chamar `enforce_role`.

**Reflex:**
- **Carregamento:** 22 handlers fazem `yield` antes do Xano.
- **Acessibilidade:**
  - `labeled` virou `<label>`;
  - `aria-label`, `type="search"` e `autocomplete` na busca e no login;
  - link "Pular para o conteúdo" com `rx.set_focus` e `<main id="conteudo">`;
  - modal com `role="dialog"`, `aria-modal` e `overscroll-behavior`;
  - `role="alert"` nos erros e `role="status"` no carregamento;
  - ícones decorativos com `aria-hidden`;
  - "…" nos textos de progresso.
- **Logo:** máximo de 45 px, caixa de 58×45 reservada, `alt` como fallback e `translate="no"`.
- **Tema:** `harley.css` com `color-scheme`, `tabular-nums`, `touch-action`, skip link e `prefers-reduced-motion`; `theme-color` no `rx.App`; pares `#121212` com branco e com laranja no teste de contraste.

**Testes:**
- `pytest.ini`, `requirements-dev.txt` (pytest 9.1.1), `tests/__init__.py`, `conftest.py` (marcadores) e `event_runner.py`.
- Testes novos: RBAC em todo endpoint autenticado; transações só do gerente; corrida da entrada; funções versionadas só dentro de `db.transaction`; carregamento (`test_loading_states.py` e o primeiro passo da venda e da transição); logo, skip link e tema.

**Docs e specs:**
- Nova spec `cadastros.md`.
- `arquitetura-e-contratos.md`: POST motos, autoria, RBAC e dados financeiros.
- `estoque-entradas.md`: cenário de corrida.
- `design-system.md`: responsividade, carregamento e acessibilidade.
- `docs/xano-api-client.md`, `docs/domain-model.md`, `docs/project-structure.md` e o anexo da auditoria.
- Documentos da Change 10 alinhados.

## Status

Aplicada e verificada em 2026-10-09.

- `python -m pytest`: 285 aprovados, 27 de integração ignorados (opt-in), 877 subtestes aprovados. `python -m unittest discover -s tests`: OK.
- `python -m py_compile`: 57 módulos, OK.
- `reflex compile --dry`: OK.
- Validador XanoScript: 123 arquivos, 0 erros.
- `xano workspace push -d ./xano --dry-run`: 8 endpoints atualizados (mais a diferença anterior de `modelos_moto.destaque`), sem exclusões e sem `--sync`.
- Responsividade (Playwright com Edge, 500 px e 1440 px, 8 páginas): sem rolagem horizontal, logo com 45 px, menu móvel só abaixo de 768 px, nenhum erro de JavaScript e o skip link levando o foco ao `<main>`.

Pendente fora do repositório:

- `xano workspace push -d ./xano` (só atualizações);
- desligar o Swagger público ou exigir token no workspace;
- rodar a integração com as credenciais `XANO_TEST_*`.
