# Tarefas

## 0. Decisões e verificações prévias

- [x] Aprovar D1: uma Change em três fases (A design system, B catálogo, C estoque e reservas); venda final na Change 9.
- [x] Aprovar D2: `modelos_moto` (catálogo) separado de `motos` (unidade com chassi e status).
- [x] Confirmar D3: catálogo público (`GET catalogo`, `GET catalogo/{id}` e `/catalogo` sem login), emendando a "superfície pública mínima".
- [x] Aprovar D4: imagens por URL `https://`, sem upload; imagens próprias ou licenciadas.
- [x] Confirmar D5: validade de 1 a 30 dias (padrão 7); cancelamento por quem reservou, pelo gerente ou por qualquer vendedor após o vencimento; sem expiração automática.
- [x] Aprovar D6: concorrência por `versao_status` e índice único `(id_moto, versao_anterior)`.
- [x] Aprovar D7: status só pelos endpoints de reserva; `POST`/`PATCH` explícitos; `PUT` bloqueado.
- [x] Aprovar D8: gestão de modelos e unidades na aba Estoque de `/vendas` (`GERENTE`).
- [x] Aprovar D9: acento Radix por CSS, Oswald e Inter (OFL), caixa alta por CSS, sem logotipo nem fonte proprietária.
- [x] Aprovar D10: texto sobre laranja sempre preto; pares de contraste garantidos por teste.
- [x] Aprovar D11: `status_badge` único, divisão de `workshop_pages.py`, preço formatado nos cadastros, fim da cor fixa do dashboard.
- [x] Aprovar D12: `XanoRateLimitError` e cache de 60 s do catálogo.
- [x] Aprovar D13: dashboard com atalhos por perfil, sem métricas.
- [x] Aprovar D14: `/catalogo` público; `/vendas` para `GERENTE`/`VENDEDOR`; `GET motos` passa a `VENDEDOR`.
- [x] Conferir na versão instalada do Reflex e do Radix Themes:
  - nomes das variáveis CSS de acento e de fonte de título;
  - `rx.App(stylesheets=…)`;
  - `backdrop_filter`;
  - `rx.drawer`;
  - `rx.tabs`.
- [x] Conferir no validador XanoScript:
  - `object[]` com schema gravado em `json`;
  - `startsWith:https://` e `pattern:` em inputs aninhados;
  - `includes` no `where`;
  - `|sort` em `foreach`.

## Fase A — design system

### A1. Tokens e folha global

- [x] Remapear `COLORS` para a nova paleta e incluir `surface_alt`, `metal_edge`, `orange_hover`, `orange_active`, `on_orange` e `overlay`.
- [x] Criar `FONTS`, `RADII`, `SHADOWS`, `STATUS_COLORS`, `TEXT_PAIRS`, `contrast_ratio`, `PRIMARY_BUTTON`, `METAL_BUTTON`, `DANGER_BUTTON`, `CARD` e `TABLE`.
- [x] Criar `assets/harley.css` (acento, fontes, caixa alta, foco, fundo).
- [x] Registrar as folhas em `rx.App(stylesheets=[…])`.

### A2. Componentes

- [x] Em `ui_helpers.py`:
  - [x] `page_header`, `section_title` e `card`;
  - [x] `primary_button`, `metal_button` e `danger_button`;
  - [x] `status_badge` único, `data_table`, `empty_state` e `stat_tile`.
- [x] Em `components.py`:
  - [x] `app_shell` e `sidebar` em seções, com item ativo e `rx.drawer` abaixo de 768 px;
  - [x] `public_shell`;
  - [x] `login_page` redesenhado;
  - [x] `modal_panel` com blur.

### A3. Telas

- [x] Login e Dashboard (atalhos por perfil).
- [x] Cadastros: `page_header`, `data_table`, preço com `format_currency`.
- [x] Entradas.
- [x] Oficina: `workshop_pages.py` (lista) e `workshop_detail.py` (detalhe), usando o `status_badge` comum.
- [x] Remover as cores fixas restantes (`components.py`, `Projeto_HarleyStore.py`).

### A4. Verificação da fase

- [x] `tests/test_theme.py` (contraste e ausência de cores fixas) e ampliação de `tests/test_ui_helpers.py`.
- [x] Suíte, `py_compile`, `reflex compile --dry`.
- [ ] Revisão visual das telas existentes em 1440 px e 390 px. Feita só para o login: as telas internas exigem credenciais do Xano.

## Fase B — catálogo

### B1. Xano

- [x] Tabela `modelos_moto` (índices `unique nome_modelo` e `familia`).
- [x] `GET catalogo` e `GET catalogo/{modelo_id}` públicos, com projeção fechada e agregação de disponíveis e "a partir de" sem N+1.
- [x] `GET`/`POST modelos_moto` e `PATCH modelos_moto/{id}` (`GERENTE`, inputs explícitos, `https` e `hex` validados).
- [x] Validar os XanoScript.

### B2. Python

- [x] `services/catalogo.py`: `FamiliaMoto`, `FAMILIA_LABELS`, `VariacaoCor`, `ModeloMotoCreate`/`Update`, `ModeloMoto`, `ModeloCatalogo` e `CatalogoCache`.
- [x] `XanoClient`: `list_catalogo`, `get_modelo_catalogo`, `list_modelos_moto`, `criar_modelo_moto` e `atualizar_modelo_moto`.
- [x] `XanoRateLimitError` (`429`) e mensagem em `error_feedback`.

### B3. Reflex

- [x] `catalogo_state.py`: funções puras e `CatalogoState` (carga via cache, família, busca, `select_cor`, detalhe).
- [x] `catalogo_pages.py`: `public_shell`, hero, abas, busca, grade responsiva, card com swatches acessíveis, modal de detalhe, CTA por perfil.
- [x] Registrar `/catalogo` e o link na sidebar.

### B4. Verificação da fase

- [x] `tests/test_catalogo.py` e `tests/test_catalogo_state.py`, contratos dos endpoints públicos e de gestão, e superfície pública explícita.
- [x] Suíte, `py_compile`, `reflex compile --dry` e validador; revisão visual de `/catalogo` em 1440 px e 390 px (estado sem dados; os cards exigem o push).

## Fase C — estoque e reservas

### C1. Xano

- [x] Evoluir `motos` com `id_modelo`, `chassi` (`trim|upper`, único), `cor`, `ano_modelo`, `preco_venda`, `status`, `id_vendedor_reserva`, `reservada_ate`, `versao_status` e `atualizado_em`.
- [x] Tabela `historico_status_moto` com índice único `(id_moto, versao_anterior)`.
- [x] Funções `Vendas/transicionar_moto` e `Vendas/detalhe_moto`.
- [x] Reescrever `GET motos` (`VENDEDOR`, enriquecido, filtros) e `GET motos/{id}`.
- [x] Reescrever `POST motos`: modelo ativo, cor do modelo, VIN, chassi único também em `motos_clientes`, ano, histórico inicial.
- [x] Reescrever `PATCH motos/{id}` (sem status, cliente ou vendedor; chassi só se `DISPONIVEL`).
- [x] Bloquear `PUT motos/{id}`.
- [x] Criar `POST motos/{id}/reserva` e `POST motos/{id}/reserva/cancelar`, com `try_catch`.
- [x] Validar os XanoScript.

### C2. Python

- [x] Reescrever `services/motos.py`: `StatusMoto`, `MotoEstoqueCreate`/`Update`, `MotoEstoque`, `MotoEstoqueDetalhe`, `HistoricoStatusMoto`, `ReservaMotoCreate` e `CancelamentoReservaMoto`.
- [x] `XanoClient`:
  - [x] criar `list_motos_estoque`, `get_moto_estoque`, `cadastrar_moto_estoque`, `atualizar_moto_estoque`, `reservar_moto` e `cancelar_reserva_moto`;
  - [x] remover `list_motos`, `create_moto` e `update_moto`.
- [x] Ajustar o teste genérico de `test_xano_client.py` que usava `Moto`.

### C3. Reflex

- [x] `vendas_state.py`:
  - [x] regras puras de permissão, cancelamento e filtros;
  - [x] payloads de reserva, modelo (editor de cores) e unidade;
  - [x] `VendasState`, que lê `?modelo=` e invalida o cache do catálogo nas escritas.
- [x] `vendas_pages.py`: abas, `data_table`, modais de reserva, cancelamento, detalhe (linha do tempo), modelo e unidade.
- [x] `ROUTE_ROLES["/vendas"]`, link na sidebar e CTA do catálogo para `/vendas?modelo=`.

### C4. Verificação da fase

- [x] `tests/test_motos.py`, `tests/test_vendas_state.py` e `tests/test_catalogo_vendas_contracts.py`; `test_authentication.py` (rotas).
- [x] Integração:
  - [x] leitura: catálogo sem token e sem campos internos;
  - [x] escrita: modelo, unidade, reserva e cancelamentos;
  - [x] concorrência: duas reservas simultâneas.
- [x] Suíte, `py_compile`, `reflex compile --dry` e validador.
- [ ] Revisão visual de `/vendas` em 1440 px e 390 px: exige credenciais e a Change publicada.

## Documentação e Archive

- [x] `docs/domain-model.md`: `modelos_moto`, `motos` (unidade, status, reserva) e `historico_status_moto`.
- [x] `docs/xano-api-client.md`: rotas públicas, catálogo, estoque, reservas, `429`, cache e matriz de acesso.
- [x] `openspec/specs/arquitetura-e-contratos.md`: superfície pública emendada.
- [x] Criar `openspec/specs/catalogo-vendas-motos.md` e `openspec/specs/design-system.md`.
- [x] Registrar em `proposal.md` o resultado aplicado, as notas e o status.
- [x] Mover para `openspec/archive/redesign-ui-catalogo-motos/`.

## Fora do repositório (usuário)

- [ ] `xano workspace push -d ./xano` (aditivo), de preferência antes num branch.
- [ ] Executar `Catalogo/seed_exemplo` (id de um `GERENTE`) e trocar os placeholders por imagens próprias ou licenciadas.
- [ ] Integração com `XANO_TEST_*`, `XANO_TEST_ALLOW_WRITES=true` e `XANO_TEST_CONCURRENCY=true`.
- [ ] Revisar visualmente as telas internas com um usuário real.
