# Tarefas — Change 11: venda de balcão de peças

Ordem de execução: 0 → 1 → 2 → 3 → 4 → 5. Cada bloco termina com a suíte offline passando (`python -m pytest`).

Regras que valem em todos os blocos:

- Commits e pushes do Xano são feitos pelo usuário. O agente prepara os arquivos e mostra o `--dry-run`.
- O plano Free publica na hora: nenhum push sem o OK do usuário sobre o `--dry-run`.
- Mudanças de banco (tabela nova, campo novo, enum ampliado) exigem dois OKs do usuário: antes de editar o esquema e antes do push.
- O usuário roda `xano auth` no próprio terminal. Valores do `.env` nunca são exibidos.
- Dúvidas de API do Reflex: skill `reflex-docs`. Compilar e rodar o app: skill `reflex-process-management` (AGENTS.md).
- Contratos, mensagens e algoritmos estão em `design.md`; as seções citadas abaixo se referem a ele.

## 0. Decisões, verificações de esquema e dry-run de base

### 0.1 Decisões (Propose)

- [x] P0: `openspec/specs/financeiro.md` criada e deltas da Change 10 aplicados em `arquitetura-e-contratos.md` e `oficina-ordens-servico.md`.
- [x] D1: toda venda de balcão é `BALCAO`; `PECAS` sem uso automático.
- [x] D2: itens na tabela nova `itens_transacao`, ligada à própria transação.
- [x] D3: preço fotografado de `produtos.preco_venda` pelo Xano, sem desconto.
- [x] D4: total conferido (`total_esperado`).
- [x] D5: idempotência por `chave_venda` com índice único `(chave_venda, id_produto)`.
- [x] D6: saída `SAIDA_VENDA` pelo livro, com saldo verificado antes e dentro da transação.
- [x] D7: cliente opcional (consumidor final).
- [x] D8: `GERENTE` e `VENDEDOR`; só o `POST`, sem endpoint de consulta.
- [x] D9: de 1 a 30 itens por venda.
- [x] D10: ampliação de enum decidida pelo `--dry-run`; `--sync` só se preciso, nunca `--delete`.

### 0.2 Linha de base do workspace

- [x] Rodar `xano workspace push -d ./xano --dry-run` com a árvore atual, sem nenhuma alteração da Change 11. O esperado é **nenhuma alteração**, o que confirma que a Change 10 está publicada e que `xano/` bate com o workspace. Qualquer diferença é resolvida com o usuário antes de seguir, para que o `--dry-run` final contenha só esta Change.
  - **Resultado (2026-10-09):** uma divergência anterior a esta Change, `UPDATE table modelos_moto`. O `pull` mostra que o local tem `bool? destaque?=false` e o remoto, `bool? destaque?` (sem padrão). O padrão entrou na Change 8 (`f034a5b`) e nunca foi aplicado pelos pushes seguintes. É inofensiva (o Reflex trata `destaque` nulo como `False`). Fica para o usuário decidir: tirar o `=false` local ou aceitar que um push com `--sync` o aplique.
- [x] Confirmar no resultado que o workspace não tem tabela `itens_transacao`, função `Balcao/*` nem endpoint `balcao/vendas`.

### 0.3 Sintaxe XanoScript (validador do MCP `xano-developer`)

Validar trechos mínimos antes de escrever os arquivos:

- [x] índice `btree|unique` composto por `text` e `int` (`chave_venda`, `id_produto`);
- [x] ampliação de `enum` em tabela e no `input` de uma função;
- [x] leitura da primeira linha por campo não único (`itens_transacao.chave_venda`), para a repetição de D5;
- [x] lista de linhas montada num `foreach` e percorrida num segundo `foreach` dentro da mesma `db.transaction`;
- [x] comparação de decimais arredondados (`|round:2`) entre um input e um total calculado;
- [x] resposta antecipada na repetição: o recibo existente é devolvido sem passar pela gravação (via `conditional` ou retorno);
  - **Resultado:** `in` em `where` e `return = {type: "single"}` validados. Não há retorno antecipado em nenhum `.xs` do projeto, então o endpoint converge para uma resposta: a repetição só define o `id_transacao` do recibo, e a gravação fica num `conditional`.
  - A ordem crescente de produtos vem do banco (`db.query produtos … sort = {id: "asc"}`, como no cancelamento de OS), e não do filtro `|sort:…:false`. A documentação desse filtro é ambígua: o argumento se chama `asc`, mas o exemplo devolve ordem decrescente.
- [x] consultar `xano_cli_docs` sobre ampliação de enum num push parcial (D10) e anotar o resultado aqui.
  - **Resultado:** o push parcial "adiciona e atualiza, mas não relaxa restrições"; `--sync` é exigido para mudanças destrutivas.

### 0.4 Primeiro OK de banco

- [x] OK do usuário para as mudanças de banco: tabela `itens_transacao`, campo `movimentacoes_estoque.id_transacao` e valor `SAIDA_VENDA` no enum `tipo` (dado no pedido de execução de 2026-10-09).

## 1. Backend Xano

### 1.1 Tabela `itens_transacao` — `xano/table/itens_transacao.xs` (nova, design §4.1)

- [x] Campos com os comentários do design:
  - `id`;
  - `id_transacao` (FK `transacoes`) e `id_produto` (FK `produtos`);
  - `quantidade` (`min:1`);
  - `valor_unitario` e `valor_total_item` (`min:0.01`);
  - `chave_venda` (`text`, `trim`);
  - `created_at` (`now`).
- [x] Índices: `primary`, `btree` em `id_transacao`, `btree` em `id_produto` e `btree|unique` em `(chave_venda, id_produto)`.
- [x] Nenhum arquivo em `xano/api` para a tabela (sem rotas genéricas).

### 1.2 Livro de movimentações — `xano/table/movimentacoes_estoque.xs` (design §4.2)

- [x] Acrescentar `SAIDA_VENDA` ao `enum tipo` e atualizar o comentário.
- [x] Incluir `int? id_transacao? {table = "transacoes"}` ("Origem SAIDA_VENDA") e o índice `btree` em `id_transacao`.

### 1.3 `Estoque/movimentar_estoque` — `xano/function/estoque/movimentar_estoque.xs` (design §4.3)

- [x] `input`: `SAIDA_VENDA` no `enum tipo` e o campo novo `int? id_transacao?`.
- [x] Subtrair o saldo quando o tipo for `SAIDA_OS` ou `SAIDA_VENDA`.
- [x] Exigir produto ativo em `SAIDA_OS` e `SAIDA_VENDA`. A devolução (`ESTORNO_OS`) a produto desativado continua permitida.
- [x] Gravar `id_transacao` no livro e atualizar o comentário de cabeçalho.
- [x] Conferir, por busca em `xano/`, que os chamadores atuais não mudam de comportamento: entrada de mercadoria, inclusão e remoção de item da OS e cancelamento da OS.

### 1.4 Dry-run do esquema (D10)

- [x] Validador XanoScript nos três arquivos de 1.1 a 1.3.
- [x] `xano workspace push -d ./xano --dry-run`. Esperado:
  - tabela nova;
  - campo e índice novos no livro;
  - enum ampliado;
  - função alterada;
  - **nenhuma exclusão**.
- [x] Registrar no design (§9) se a ampliação do enum aparece no push parcial ou se exige `--sync`. Na dúvida, confirmar num branch (`xano workspace push -d ./xano -b <branch>`), como sugere `docs/xano-api-client.md`.
  - **Resultado:** a ampliação aparece como `UPDATE_FIELD` no push parcial, sem nenhum pedido de `--sync` (além de `CREATE itens_transacao`, `ADD_FIELD` e `UPDATE` da função). Como o `UPDATE modelos_moto` também aparece e nunca é aplicado, a confirmação real fica para depois do push (1.7). O branch não foi testado porque criar um branch altera o workspace.

### 1.5 `Balcao/detalhe_venda` — `xano/function/balcao/detalhe_venda.xs` (nova, design §4.5)

- [x] `input`: `id_transacao`. Precondição: a transação existe e é `BALCAO`.
- [x] `transacoes` com `left join` em `clientes` e `funcionarios`, para `nome_cliente` e `nome_funcionario`.
- [x] `itens_transacao` da transação com `join` em `produtos` (`codigo`, `nome_produto`), ordenados por `id`.
- [x] Resposta no formato da "Saída" de §4.4; somente leitura.

### 1.6 `POST balcao/vendas` — `xano/api/harley/balcao/vendas_POST.xs` (novo, design §4.4)

- [x] Cabeçalho: grupo `HARLEY`, `auth = "user"` e comentário com as regras e a concorrência.
- [x] `input`:
  - `text chave_venda filters=trim|max:64`;
  - `int? id_cliente?`;
  - `decimal total_esperado filters=min:0.01`;
  - `object[] itens` com `int id_produto filters=min:1` e `int quantidade filters=min:1`.
- [x] `enforce_role "VENDEDOR"`; leitura de `user.id_funcionario` com precondição `accessdenied`.
- [x] Pré-validações, na ordem do §4.4 (item 1) e com as mensagens da tabela de erros:
  - [x] chave não vazia;
  - [x] repetição: se a chave já tem itens, responde o recibo da venda existente sem gravar nada;
  - [x] de 1 a 30 itens, sem produto repetido;
  - [x] cliente informado existe e está ativo;
  - [x] cada produto existe e está ativo, com saldo suficiente (`estoque_qtd ?? 0`), acumulando `quantidade × preco_venda`;
  - [x] total acumulado (`round:2`) igual a `total_esperado`.
- [x] `try_catch` + `db.transaction`:
  - [x] relê `preco_venda` e `ativo` em ordem de `id_produto` e monta as linhas e o total;
  - [x] confere o total de novo;
  - [x] `db.add transacoes` (`BALCAO`, `id_funcionario` do JWT, `id_cliente` ou nulo, `data_transacao = now` e `valor_total`);
  - [x] para cada linha, `db.add itens_transacao` (com `chave_venda`) e `Estoque/movimentar_estoque` (`SAIDA_VENDA`, `id_transacao`).
- [x] `catch` → `400` com a mensagem de conflito do §4.4.
- [x] Resposta: `Balcao/detalhe_venda` da transação criada.
- [x] Validador XanoScript no endpoint e na função.

### 1.7 Publicação (usuário)

- [ ] `--dry-run` final revisado com o usuário: só objetos da Change 11 e nenhuma exclusão.
- [ ] Segundo OK do usuário e push feito por ele: `xano workspace push -d ./xano`, com `--sync` (sem `--delete`) somente se 1.4 indicar.
- [ ] Atualizar nos arquivos novos os `guid` atribuídos pelo push, como na Change 10.
- [ ] Depois do push, `xano workspace pull` numa pasta temporária e conferir que `movimentacoes_estoque.tipo` tem `SAIDA_VENDA` e que `id_transacao` existe. Se o enum não tiver sido aplicado, publicar com `--sync`, sem `--delete`.

## 2. Frontend Reflex

### 2.1 Helpers de produto compartilhados (design §5.3)

- [x] Mover `produto_row`, `filtrar_produtos` e `PRODUTO_SEARCH_LIMIT` de `workshop_state.py` para `listing.py`. Motivo: a spec `arquitetura-e-contratos` proíbe um estado importar de outro estado de página.
- [x] `workshop_state.py` passa a importá-los de `listing.py`, sem mudança de comportamento; a suíte da oficina continua passando.

### 2.2 DTOs — `Projeto_HarleyStore/services/balcao.py` (novo, design §5.1)

- [x] `MAX_ITENS_VENDA = 30`.
- [x] `ItemVendaBalcaoCreate` e `VendaBalcaoCreate`, com validadores de produto sem repetição e de `total_esperado` com 2 casas.
- [x] `ItemVendaBalcao` e `VendaBalcaoDetalhe` (`extra="ignore"`, cliente e nomes anuláveis).

### 2.3 Cliente HTTP — `services/xano_client.py`

- [x] `vender_balcao(venda) -> VendaBalcaoDetalhe`: `POST balcao/vendas` no mesmo padrão de `vender_moto`, com docstring e erros tipados.

### 2.4 Carrinho: funções puras — `Projeto_HarleyStore/balcao_state.py` (novo, design §5.3)

- [x] `BalcaoFormError` e `nova_chave()` (`uuid.uuid4()`).
- [x] `adicionar_item`: soma ao item existente e recusa quantidade acima do saldo e o 31º produto.
- [x] `alterar_quantidade`, `remover_item` e `total_carrinho`.
- [x] `build_venda_payload`: "Consumidor final" vira `id_cliente = None`; erros com mensagens legíveis (`option_id` de `listing.py`).
- [x] `recibo_view`: número, data, cliente ("Consumidor final" quando nulo), vendedor, linhas e total formatados.

### 2.5 Carrinho: estado e eventos — `BalcaoState(AuthState)`

- [x] Variáveis: `catalogo`, `busca`, `carrinho`, `cliente_options`, `cliente`, `chave_venda`, `confirm_open`, `recibo`, `is_busy` e `list_error`.
- [x] `load_balcao` (`on_load`, depois de `restore_session`; respeita `role_allows_route`): carrega produtos e clientes ativos e trata erro e `429`.
- [x] `set_busca`, `adicionar`, `set_quantidade`, `remover`, `set_cliente` e `limpar_carrinho` (este renova a chave).
- [x] `abrir_confirmacao`: valida pelo `build_venda_payload` e abre o painel.
- [x] `confirmar_venda`:
  - [x] trava de reentrada (`operation_is_blocked`), `is_busy = True` e `yield` **antes** de chamar o Xano;
  - [x] em caso de sucesso: recibo, `toast_success`, carrinho limpo, nova chave e produtos recarregados;
  - [x] em caso de erro: `error_feedback`, mantendo a mesma chave; em saldo, preço ou conflito, recarregar os produtos.
- [x] `fechar_recibo`.
- [x] Toasts somente pelo `feedback.py`; nenhum `rx.toast` direto.

### 2.6 Tela — `Projeto_HarleyStore/balcao_pages.py` (novo, design §5.4)

- [x] `page_header("Venda no balcão", …)` e layout em duas colunas que vira uma só em 500 px.
- [x] Coluna "Peças": `toolbar` de busca e resultados com código, nome, saldo e preço; "Adicionar" desativado como "Sem saldo" quando o saldo é zero.
  - Acrescentado no Apply, a pedido do usuário ("filtro e busca local"): filtro por categoria (`produto_row` ganhou `categoria`) e lista limitada a 20 resultados, com aviso para refinar a busca.
- [x] Coluna "Carrinho":
  - `data_table` com quantidade editável, subtotal e remover;
  - `labeled("Cliente", select)` com "Consumidor final";
  - `stat_tile("Total", …, accent=True)`;
  - botões "Limpar" e "Fechar venda" (este desativado com carrinho vazio ou durante o envio);
  - `empty_state` com carrinho vazio.
- [x] Painel de confirmação e recibo em `modal_panel` (`role="dialog"`), com estado de carregamento em "Confirmar venda".
- [x] `error_callout` para falha de carga e tudo dentro de `guarded_page(…, "/balcao")`.

### 2.7 Shell, rotas e financeiro (design §5.5)

- [x] `auth.py`: `ROUTE_ROLES["/balcao"] = frozenset({"GERENTE", "VENDEDOR"})`.
- [x] `components.py`: ("Balcão", "/balcao", "shopping-cart") na seção "Vendas" ("Vendas → Balcão", rótulo pedido pelo usuário no Apply); ícone aceito pelo `reflex compile`.
- [x] `dashboard_pages.py`: atalho "Balcão" em `SHORTCUTS`. O título da página continua "Venda no balcão".
- [x] `Projeto_HarleyStore.py`: `app.add_page` com `on_load=[AuthState.restore_session, BalcaoState.load_balcao]`.
- [x] `financeiro_state.py`: "Venda no balcão #N" em `descricao_operacao`; "Consumidor final" como contraparte nula de `BALCAO` em `operacao_row`.

### 2.8 Checagem do bloco

- [x] `python -m py_compile` nos módulos novos e alterados.
- [x] `reflex compile --dry` (skill `reflex-process-management`).

## 3. Suíte de testes

### 3.1 Contratos XanoScript — `tests/test_balcao_contracts.py` (novo)

- [x] **Esquema:**
  - `itens_transacao` com chaves estrangeiras, mínimos e índice único `(chave_venda, id_produto)`;
  - `movimentacoes_estoque` com `SAIDA_VENDA` e `id_transacao` (FK e `btree`).
- [x] **`movimentar_estoque`:**
  - subtrai e exige produto ativo em `SAIDA_VENDA`;
  - grava `id_transacao`;
  - `ENTRADA`, `SAIDA_OS` e `ESTORNO_OS` não mudam.
- [x] **Endpoint:**
  - `enforce_role "VENDEDOR"` e autor do JWT;
  - `input` sem preço nem total por item;
  - limites de 1 a 30 itens;
  - pré-validações (repetição, saldo, cliente, total) antes do `try_catch`;
  - na `db.transaction`: `transacoes` `BALCAO`, itens em ordem de `id_produto` e `movimentar_estoque` `SAIDA_VENDA` com `id_transacao`;
  - total conferido dentro da transação;
  - `catch` com a mensagem de conflito.
- [x] **`Balcao/detalhe_venda`:** somente leitura e precondição `BALCAO`.
- [x] **Rotas:** nenhuma rota genérica para `itens_transacao`; todo `function.run` aponta para uma função existente.

### 3.2 DTOs e cliente — `tests/test_balcao.py` (novo)

- [x] `VendaBalcaoCreate`: limites, produto repetido, quantidade e total positivos, chave obrigatória e decimais.
- [x] `VendaBalcaoDetalhe` com cliente nulo e decimais.
- [x] `XanoClient.vender_balcao` com `MockTransport`: rota, JSON, token, `400`, `403`, `429` e resposta fora do contrato.

### 3.3 Estado do carrinho — `tests/test_balcao_state.py` (novo)

- [x] Funções puras:
  - soma do mesmo produto;
  - limite de saldo e de 30 itens;
  - alterar, remover e total;
  - payload com consumidor final e com cliente, e suas mensagens;
  - `recibo_view`.
- [x] Chave mantida após erro e renovada após sucesso e após limpar.
- [x] Carga só para `GERENTE` e `VENDEDOR`.
- [x] `confirmar_venda` via `tests.event_runner.run_event`:
  - `yield` antes da chamada;
  - recibo e recarga dos produtos no sucesso;
  - erro de saldo e de preço visível, com recarga.

### 3.4 Ajustes em testes existentes

- [x] `tests/test_loading_states.py`: `confirmar_venda` na regra "`yield` antes do Xano".
- [x] `tests/test_financeiro_state.py`: "Venda no balcão #N" e "Consumidor final".
- [x] Segurança e contratos existentes (onde as regras já estavam testadas):
  - matriz com `/balcao`: `tests/test_authentication.py`;
  - enum e trava de produto ativo de `movimentar_estoque`: `tests/test_estoque_contracts.py`;
  - endpoint do balcão na lista de gravadores de `transacoes`: `tests/test_financeiro_contracts.py`;
  - nenhuma rota genérica para `itens_transacao`: `tests/test_balcao_contracts.py`. Os testes globais de `test_security_contracts.py` e `test_catalogo_vendas_contracts.py` (`enforce_role` em todo endpoint e funções chamadas existentes) já cobrem o endpoint novo.
- [x] `tests/test_layout.py`: `/balcao` em `PAGES` (14 rotas com o logo).
- [x] `tests/test_workshop_state.py`: helpers importados de `listing.py`.

### 3.5 Integração — `tests/test_integration_xano.py`

Opt-in como os demais cenários; sem credenciais, os testes são ignorados com o motivo.

- [x] Sem escrita (`XANO_TEST_LIVE`):
  - `MECANICO` recebe `403` em `POST balcao/vendas`;
  - payload inválido (vazio, produto repetido, mais de 30 itens) recebe `400`.
- [x] Com escrita (`XANO_TEST_ALLOW_WRITES`), reaproveitando `restocked_products`, `stock_of` e `active_client_id`:
  - venda com cliente e com consumidor final: transação `BALCAO`, itens, livro com `id_transacao`, saldo reduzido e presença no `GET financeiro/resumo`;
  - saldo insuficiente e `total_esperado` divergente sem efeito;
  - repetição da mesma `chave_venda`: mesma `id_transacao` e uma única baixa.
- [x] Com concorrência (`XANO_TEST_CONCURRENCY`), com `race`: duas vendas simultâneas pedindo o saldo inteiro do mesmo produto. Uma é aceita, a outra recusada, e o saldo final é zero.

## 4. Verificação e documentação

### 4.1 Verificação

- [x] `python -m pytest` e `python -m unittest discover -s tests` sem falhas (integração ignorada por opt-in).
- [x] `python -m py_compile` em todos os módulos.
- [x] `reflex compile --dry`.
- [x] Validador XanoScript em todos os `.xs` novos e alterados, e `--dry-run` repetido depois dos ajustes.
- [ ] Verificação visual de `/balcao` em desktop e em 500 px: busca, carrinho, confirmação, recibo e erros. Usar dados de demonstração e remover ao final qualquer rota temporária.
- [ ] Navegação: `VENDEDOR` e `GERENTE` veem "Venda no balcão"; `MECANICO` não.

### 4.2 Documentação

- [ ] `docs/domain-model.md`:
  - seção nova *Itens_Transacao*;
  - *Transacoes*: origem `BALCAO` e itens; remover "transações não possuem linhas de itens";
  - *Movimentacoes_Estoque*: `SAIDA_VENDA` e `id_transacao`.
- [ ] `docs/xano-api-client.md`: `vender_balcao`, DTOs, matriz de acesso, checklist de deploy da Change 11 (com o resultado de D10) e testes.
- [ ] `docs/project-structure.md`: `balcao_state.py`, `balcao_pages.py`, `services/balcao.py` e os helpers de produto em `listing.py`.

### 4.3 Deltas de spec (`specs/` desta change)

- [ ] `vendas-balcao.md` (nova): requisitos e cenários da proposta (venda com e sem cliente, saldo, preço, repetição, concorrência, limites e acesso).
- [ ] `estoque-entradas.md`: saída `SAIDA_VENDA` e origem `id_transacao` no livro.
- [ ] `financeiro.md`: `BALCAO` como origem de transação (venda no balcão) e descrição no `/financeiro`.
- [ ] `arquitetura-e-contratos.md`: rota `/balcao`, matriz e itens de transação sem rotas genéricas.

## 5. Arquivamento

- [ ] Conferir que a implementação corresponde exatamente às specs e ao design (`openspec/config.yaml`, `archive`).
- [ ] Aplicar os deltas de 4.3 em `openspec/specs/` **no mesmo passo** do arquivamento, para não repetir a pendência da Change 10.
- [ ] Atualizar a "Situação" do design e o "Status" da proposta.
- [ ] Mover `openspec/changes/venda-balcao-pecas/` para `openspec/archive/venda-balcao-pecas/`, depois do push e da integração.
- [ ] Commit feito pelo usuário.

## Fora do repositório (usuário)

- [ ] `xano auth`, se o token do CLI tiver expirado.
- [ ] Revisar o `--dry-run` e publicar (bloco 1.7).
- [ ] Rodar a integração com `XANO_TEST_ALLOW_WRITES=true` e `XANO_TEST_CONCURRENCY=true`.
- [ ] Fazer uma venda real no `/balcao` e conferi-la no `/financeiro`.
