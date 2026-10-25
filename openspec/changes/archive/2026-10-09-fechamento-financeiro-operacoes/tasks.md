# Tarefas

Ordem de execução: 0 → 1 → 2 → 3 → 4 → 5. Cada bloco termina com a suíte offline passando.

## 0. Decisões e verificações prévias (antes do Apply)

- [x] Aprovar D1: escopo de fechamento financeiro; venda no balcão na Change 11.
- [x] Aprovar D2: lançamento `ORDEM_SERVICO` na conclusão, dentro da `db.transaction`; OS com total zero conclui sem lançamento.
- [x] Aprovar D3: autoria do lançamento = funcionário que concluiu (JWT).
- [x] Aprovar D4: entradas não geram `COMPRA`; o resumo lê `entrada_mercadoria` diretamente.
- [x] Aprovar D5: `POST`/`PUT`/`PATCH transacoes` em `403`; correção só por estorno futuro.
- [x] Aprovar D6: leitura de transações e resumo somente para `GERENTE`.
- [x] Aprovar D7: período de até 366 dias; lista de até 500 operações; totais sobre o período inteiro.
- [x] Aprovar D8: `btree` simples (não único) em `transacoes.id_os`.
- [x] Aprovar D9: limites do período em UTC−3 fixo, sem `tzdata`.
- [x] Aprovar D10: função idempotente de lançamento retroativo das OS concluídas.
- [x] No validador XanoScript (MCP `xano-developer`), confirmar:
  - `function.run` e `db.add` dentro de `conditional` numa `db.transaction`;
  - `left join` com `eval` em `db.query` com filtro por intervalo de timestamp;
  - `|sort` e `|slice` sobre lista montada em `foreach`;
  - comparação e subtração de `timestamp` de input.
- [x] Na versão instalada do Reflex, confirmar `rx.input(type="date")` com `on_change` recebendo `AAAA-MM-DD` e o ícone `chart-column` do Lucide.

## 1. Backend Xano

### 1.1 Tabela `transacoes`

- [x] Incluir `int? id_os? {table = "ordens_servico"}` com comentário (Change 10).
- [x] Incluir o índice `{type: "btree", field: [{name: "id_os"}]}`.

### 1.2 Conclusão de OS — `POST ordens_servico/{id}/status`

- [x] Ler a OS com `id_cliente` e `id_moto_cliente`; resolver `$id_cliente = $os.id_cliente ?? motos_clientes.id_cliente`.
- [x] Dentro da `db.transaction`, depois do `db.patch ordens_servico`, somente para `CONCLUIDA`:
  - [x] recalcular os totais com `Oficina/totais_os`;
  - [x] se `valor_total > 0`, `db.add transacoes` com `tipo_transacao = ORDEM_SERVICO`, `id_funcionario` do JWT, `id_cliente`, `id_moto_cliente`, `id_os`, `data_transacao = $agora` e `valor_total`.
- [x] Manter o `try_catch` e a mensagem atuais; atualizar o comentário do cabeçalho do endpoint.

### 1.3 Detalhe da OS — `Oficina/detalhe_os`

- [x] Consultar `transacoes` por `id_os` e acrescentar `id_transacao` e `data_lancamento` (nulos sem lançamento).

### 1.4 Bloqueio do CRUD manual de `transacoes`

- [x] `POST transacoes`: `enforce_role` + `precondition (false)` `accessdenied` "Transações são registradas somente pelas operações de venda e de oficina."
- [x] `PUT transacoes/{id}` e `PATCH transacoes/{id}`: `enforce_role` + `precondition (false)` `accessdenied` "Transações são imutáveis."
- [x] `DELETE transacoes/{id}`: atualizar a mensagem (sem "Change de vendas") — feito no saneamento pós-Change 9.
- [x] `GET transacoes` e `GET transacoes/{id}`: `required_role: "GERENTE"`; lista ordenada por `data_transacao` desc — feito no saneamento pós-Change 9.
- [x] Preservar rota e `guid` de todos os arquivos.

### 1.5 Visão consolidada — `GET financeiro/resumo`

- [x] Função `Financeiro/resumo_operacoes` (`xano/function/financeiro/resumo_operacoes.xs`):
  - [x] validar `fim >= inicio` e `fim − inicio ≤ 366 dias` (`400` com as mensagens do design);
  - [x] consultar `transacoes` do período com nomes de cliente e funcionário e com modelo e placa da moto do cliente;
  - [x] consultar `entrada_mercadoria` do período com nomes de fornecedor e funcionário;
  - [x] montar as operações, acumular `por_tipo`, `receitas`, `despesas` e `saldo` (`round:2`), com a natureza por tipo;
  - [x] ordenar por data desc, preencher `total_operacoes`, cortar em 500 e preencher `truncado`.
- [x] Endpoint `xano/api/harley/financeiro/resumo_GET.xs`: grupo `HARLEY`, `auth = "user"`, `enforce_role` `GERENTE`, inputs `inicio` e `fim`, sem escrita.

### 1.6 Migração das OS legadas

- [x] Função `Financeiro/lancar_os_concluidas_legadas` (`xano/function/financeiro/lancar_os_concluidas_legadas.xs`):
  - [x] input `id_funcionario` (GERENTE responsável);
  - [x] para cada OS `CONCLUIDA` sem transação com o mesmo `id_os` e com `totais_os.valor_total > 0`, gravar a transação com `data_transacao = data_encerramento ?? data_abertura`;
  - [x] responder a quantidade lançada e os ids ignorados (total zero);
  - [x] idempotente; não chamada por nenhum endpoint.

### 1.7 Validação do backend

- [x] Validador XanoScript em todo o `xano/` e diagnósticos do VS Code sem erros.
- [x] `xano workspace push -d ./xano --dry-run`: somente criações e atualizações esperadas, sem exclusões e sem `--sync`.

## 2. Frontend Reflex

### 2.1 Serviço — `Projeto_HarleyStore/services/financeiro.py`

- [x] `TipoOperacao`, `Natureza`, `TIPO_LABELS`, `NATUREZA_POR_TIPO`, `PERIODO_MAXIMO_DIAS` e `FUSO_LOJA` (UTC−3).
- [x] `PeriodoFinanceiro` com validadores (ordem e 366 dias) e `params()` em ms (início às 00:00 e fim às 23:59:59.999 no fuso da loja).
- [x] `TotalPorTipo`, `OperacaoFinanceira` (`extra="ignore"`, campos de referência opcionais) e `ResumoFinanceiro`.

### 2.2 Integração no `XanoClient`

- [x] `resumo_financeiro(periodo) -> ResumoFinanceiro` (`GET financeiro/resumo` com `params`).
- [x] Nenhum método de escrita de transações.

### 2.3 Indicador na Oficina

- [x] `OrdemServicoDetalhe`: `id_transacao` e `data_lancamento` opcionais.
- [x] Linha do detalhe da OS (`workshop_state.py`) com o texto do lançamento: "Faturada · transação #N · data", ou "Concluída sem lançamento financeiro (total zero)".
- [x] `workshop_detail.py`: exibir o indicador nas OS concluídas.
- [x] `transition_panel`: para `CONCLUIDA`, "O total de R$ X será lançado como receita de serviço." ou "Total zero: a OS será concluída sem lançamento."

### 2.4 Página `/financeiro` (exclusiva do GERENTE)

- [x] `financeiro_state.py`, funções puras:
  - `periodo_padrao`, `atalho_periodo` (`MES_ATUAL`, `MES_ANTERIOR`, `ULTIMOS_30_DIAS`) e `build_periodo` com `FinanceiroFormError`;
  - `descricao_operacao`, `operacao_row`, `tipo_row` e `filtrar_operacoes` (filtro local por tipo e busca).
- [x] `FinanceiroState(AuthState)`:
  - `load_financeiro` (`on_load`, respeitando `role_allows_route`), `set_inicio`, `set_fim`, `aplicar_periodo`, `usar_atalho`, `set_filtro_tipo` e `set_busca`;
  - erros por `error_feedback`; sessão expirada por `_xano_error_response`.
- [x] `financeiro_pages.py`:
  - `page_header`, barra de período (datas, atalhos e "Aplicar");
  - `stat_tile` de Receitas, Despesas e Saldo (saldo negativo em `danger`);
  - tabela por tipo;
  - lista de operações com abas roláveis por tipo (`rx.tabs`, no lugar do `rx.segmented_control` previsto, para caber em 500 px), `toolbar`, `data_table`, sinal e cor por natureza;
  - aviso de truncamento, `empty_state` e `error_callout`, tudo em `guarded_page(…, "/financeiro")`.
- [x] `Projeto_HarleyStore.py`: registrar `/financeiro` com `on_load=[AuthState.restore_session, FinanceiroState.load_financeiro]`.

### 2.5 Navegação, rota e tema

- [x] `auth.py`: `ROUTE_ROLES["/financeiro"] = frozenset({"GERENTE"})`.
- [x] `components.py`: seção "Gestão" com ("Financeiro", "/financeiro", "chart-column") antes de "Administração".
- [x] `dashboard_pages.py`: atalho "Financeiro" em `SHORTCUTS`.
- [x] `styles/theme.py`: `RECEITA` e `DESPESA` em `STATUS_COLORS` (pares entram em `TEXT_PAIRS`).

## 3. Suíte de testes

### 3.1 Testes unitários e de contrato (offline)

- [x] `tests/test_financeiro_contracts.py` (novo):
  - `transacoes.id_os` anulável com `btree` não único;
  - `POST`/`PUT`/`PATCH transacoes` em `403` com `enforce_role` e `guid`;
  - `GET transacoes[/{id}]` com `GERENTE`;
  - lançamento só em `CONCLUIDA`, dentro da `db.transaction`, depois do `patch`, com `totais_os`, `valor_total > 0` e `id_funcionario` do JWT;
  - resumo: `GERENTE`, validação do período, duas fontes, `slice` de 500 e nenhuma escrita;
  - função de D10 idempotente e fora dos endpoints;
  - todo `function.run` aponta para função existente (reaproveitar o teste da Change 9).
- [x] `tests/test_financeiro.py` (novo):
  - `PeriodoFinanceiro` (ordem, limite de 366 dias, `params` em UTC−3 e fim às 23:59:59.999);
  - DTOs com campos nulos e decimais;
  - `XanoClient.resumo_financeiro` com `MockTransport`: rota, query string, token, `400`, `403`, `429` e resposta fora do contrato.
- [x] `tests/test_financeiro_state.py` (novo):
  - período padrão e atalhos (virada de mês e de ano);
  - mensagens de `build_periodo`;
  - `descricao_operacao` por tipo e para o legado;
  - filtro e busca locais;
  - carga só para `GERENTE`;
  - erro e `429` visíveis;
  - saldo negativo;
  - aviso de truncamento.
- [x] `tests/test_ordens_servico.py` / `tests/test_workshop_state.py`: `id_transacao` no detalhe; textos do indicador e do painel de conclusão (com e sem total).
- [x] `tests/test_hardening_contracts.py` / `tests/test_security_contracts.py`: rotas de `transacoes` bloqueadas e matriz atualizada.
- [x] `tests/test_layout.py`: `/financeiro` em `PAGES` (13 rotas com o logo).
- [x] `tests/test_theme.py`: contraste WCAG de `RECEITA` e `DESPESA`.

### 3.2 Testes de integração (`tests/test_integration_xano.py`)

- [x] Sem escrita:
  - `VENDEDOR` e `MECANICO` recebem `403` em `GET financeiro/resumo` e em `GET transacoes`;
  - `POST transacoes` recebe `403`;
  - período invertido ou maior que 366 dias recebe `400`;
  - o `GERENTE` lê o resumo do mês.
- [x] Com escrita (`XANO_TEST_ALLOW_WRITES`):
  - concluir uma OS com peça e serviço gera uma única transação `ORDEM_SERVICO` com o total, visível no detalhe e no resumo;
  - OS sem itens conclui sem transação;
  - cancelar não gera transação.
- [x] Com concorrência (`XANO_TEST_CONCURRENCY`): duas conclusões simultâneas geram uma transição e uma transação.

## 4. Verificação

- [x] `python -m pytest` e `python -m unittest discover -s tests` sem falhas (332 aprovados, 33 de integração ignorados por opt-in).
- [x] `python -m py_compile` em todos os módulos.
- [x] `reflex compile --dry`.
- [x] Verificação visual de `/financeiro` (desktop e celular) e do detalhe da OS concluída, com rota temporária removida ao final.
- [x] Validador XanoScript e `--dry-run` repetidos após os ajustes.

## 5. Documentação e arquivamento

- [x] `docs/domain-model.md`: *Transacoes* (origem, imutabilidade, `id_os`), *Visão Consolidada* e conclusão da OS.
- [x] `docs/xano-api-client.md`: `resumo_financeiro`, DTOs, matriz, checklist de deploy da Change 10 e testes.
- [x] `docs/project-structure.md`: novos módulos.
- [x] Deltas escritos em `specs/` desta change (`financeiro.md` nova, `oficina-ordens-servico.md` e `arquitetura-e-contratos.md`).
- [x] Aplicar os deltas em `openspec/specs/` no arquivamento (aplicados em 2026-10-09, como P0 da Change 11).
- [ ] Arquivar a change em `openspec/archive/` depois do push e da integração.

## Fora do repositório (usuário)

- [ ] Revisar o `--dry-run` e publicar com `xano workspace push -d ./xano` (o plano Free publica na hora).
- [ ] Executar `Financeiro/lancar_os_concluidas_legadas` uma vez (Run & Debug), informando o id de um `GERENTE`.
- [ ] Conferir no resumo as transações antigas criadas pelo CRUD genérico.
- [ ] Rodar a integração com `XANO_TEST_ALLOW_WRITES=true` e `XANO_TEST_CONCURRENCY=true`.
