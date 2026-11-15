# Tarefas — Change 16: otimização, JOINs e concorrência no backend Xano

As seções agrupam as tarefas por tema. O que foi publicado está em **Entregas publicadas** (Entregas 1 e 2; nos commits, "fase 1" e "fase 2"). O que falta são as decisões e o push do banco e os testes de escrita e concorrência.

## Aprovação

- [x] Aprovação do escopo dos itens 9 a 16 (2026-11-14), com as decisões: preço e cor bloqueados em moto reservada ou vendida (13), saldo inicial 0 (14) e teto de 50 itens na entrada (16).
- [ ] Decisões de banco (itens 5, 7 e 8) pelo usuário.

## Concluído antes da ampliação

- [x] `GET motos` com `join` e `eval` (item 1); teste estático de contrato (mesmos campos, sem consulta de tabela inteira). Publicado: o `--dry-run` de 2026-10-27 não mostrou diferenças.
- [x] Log `ERROR` dos 5xx com a `message` do Xano, para que o próximo 500 traga a causa: uma linha, mascaramento de e-mail, placa, chassi e sequências de 3+ dígitos, corte em 200 caracteres e corpo não JSON fora do log. Testes com mutação (as 6 variantes sem cada proteção falham).
- [x] Auditoria E2E de 2026-10-27, com o VENDEDOR de teste (A1): a `enforce_role` recusava com `throw`, e o Xano respondia HTTP 200 com `{payload, statement}`. Passa a recusar com `precondition` `accessdenied` (403), mantendo a exceção do `admin`. Contrato estático impede a volta do `throw` e exige cada ramo de perfil (ALL, GERENTE, VENDEDOR, MECANICO) com `accessdenied`; as 5 mutações são pegas. Publicado; `GET fornecedores` como VENDEDOR responde 403.
- [x] Auditoria E2E (A2): `Vendas/detalhe_moto` com joins à esquerda (modelo, cliente e vendedor) numa só consulta; antes, toda unidade sem reserva respondia 400 "Missing param: field_value". Contrato estático sem `db.get` desses vínculos. Publicado; `test_seller_opens_the_detail_of_a_unit_without_a_reservation` passa ao vivo.
- [x] Auditoria E2E (M1 e B2): `SHOWROOM_FIELDS` da integração com `galeria`; miniatura da foto do modelo na tabela de `/vendas`.

## Auditoria do código `.xs`

- [x] Mapeamento de leituras por registro e sem join em `xano/function/` e `xano/api/` (2026-11-11); resultado na proposta.
- [x] Mapeamento das alterações de status e de estoque: todas passam por `Estoque/movimentar_estoque`, `Vendas/transicionar_moto` ou pelo índice de `historico_status_os`; lacunas nos itens 13 e 14.
- [x] Baseline local: `ruff` sem violações, `compileall` OK, `pytest` com 441 aprovados e 43 ignorados.
- [x] Contrato estático de recusas (item 15): nenhum `throw` em `xano/`, `error_type` em toda `precondition` (164 conferidas); `generate_magic_link` com `inputerror`. O teste confere o próprio leitor com um exemplo, e a mutação em memória (`precondition` sem tipo em `generate_magic_link` e em `enforce_role`) é pega.
- [x] Repetir, só leitura e cadenciados, os 5 testes de controle de acesso da integração (`XANO_TEST_LIVE`), na parte do VENDEDOR. Em 2026-11-15, com 15 s entre as execuções, o VENDEDOR recebeu 403 (`XanoPermissionError`, levantado só para HTTP 403) em todas as recusas esperadas:
  - `GET fornecedores` e `GET funcionarios` (`test_suppliers_and_employees_are_manager_only`);
  - resumo financeiro e `GET transacoes` (`test_financial_data_is_manager_only`);
  - mecânicos, abertura e transição de OS (`test_salesperson_cannot_operate_orders`);
  - inclusão e remoção de item (`test_salesperson_cannot_change_items`).

  O `POST entrada_mercadoria` já tinha dado 403 em 2026-11-14 (`test_non_managers_cannot_register_receipts`). O pytest marca `test_suppliers_and_employees_are_manager_only` como pulado porque a parte final, a leitura permitida ao GERENTE, não tem credenciais. O subteste do VENDEDOR passou.
- [x] Os mesmos testes com MECANICO e GERENTE, depois que as credenciais dos dois entraram no `.env`. Em 2026-11-15, com 20 s entre as execuções:
  - MECANICO recebeu 403 em fornecedores e funcionários, no resumo financeiro e em `GET transacoes`, na lista de motos do estoque e no `POST entrada_mercadoria`;
  - GERENTE leu fornecedores e funcionários e o resumo financeiro, e o período invertido ou maior que 366 dias recebeu 400;
  - os 3 perfis leram a oficina (`test_every_profile_reads_the_workshop`).

  Testes: `test_suppliers_and_employees_are_manager_only`, `test_financial_data_is_manager_only`, `test_manager_reads_the_summary_and_the_period_is_validated`, `test_sales_are_for_sellers_and_managers_only` e `test_non_managers_cannot_register_receipts`, todos aprovados.

  `test_every_profile_reads_shared_resources` passou com GERENTE e VENDEDOR, mas o subteste do MECANICO recebeu 429 duas vezes, mesmo isolado: são 3 logins e 12 leituras em cerca de 5 s, acima do limite do plano Free. As mesmas 4 leituras do MECANICO passaram num script de leitura com 3 s entre as requisições.

  `test_mechanic_cannot_sell_at_the_counter` pulou porque produção não tem produto ativo. A recusa do MECANICO no balcão continua sem prova ao vivo.

## Refatoração com JOINs

- [x] Confirmar join da mesma tabela com dois apelidos. Validador do MCP: OK. A extensão do VSCode avisa "Unknown table", mas o leitor dela trata todo `$db.X` como tabela e não conhece joins. O sandbox do Xano exige plano pago. Depois do push de 2026-11-14:
  - o Xano guardou os 7 objetos sem mudança (`--dry-run` seguinte: "No changes to push");
  - `test_unknown_order_detail_is_not_found` passa (404, sem 500);
  - `test_every_profile_reads_the_workshop` passa como VENDEDOR e, desde 2026-11-15, com os 3 perfis.

  Falta ver os nomes de autor e mecânico preenchidos pelos apelidos, o que exige uma OS no banco (produção tem zero).
- [x] `Oficina/detalhe_os` (item 9): uma consulta com 5 joins à esquerda (`motos_clientes`, `cliente_os`, `dono_moto`, `autor`, `mecanico`), `return single` antes do `notfound`, mesmos campos e fallback do cliente pelo dono da moto; os campos auxiliares saem da resposta. Contrato estático com mutações (join interno, campo auxiliar na resposta, fallback trocado).
- [x] `GET ordens_servico` (item 10): `autor` e `mecanico` por joins com apelido, sem a leitura de `funcionarios` nem o laço. Contrato estático com mutação.
- [x] `GET entrada_mercadoria` (item 11): os itens numa só consulta, contados num mapa por entrada (não há agregação com group by documentada no XanoScript). A chave leva o prefixo `e`, porque um caminho só com dígitos pode ser lido como índice de array (revisão de 2026-11-14). Contrato estático com mutações. Com zero entradas em produção, a contagem ainda não rodou ao vivo.
- [x] Pré-checagens de produto do balcão e da entrada (item 12) numa só consulta (`id in $ids_produto`), conferidas na ordem do pedido e com a mesma mensagem por produto. O mapa de quantidades do balcão passou a usar chaves `"p" ~ id`, sem `|to_text`, no mesmo padrão da contagem de entradas. Contratos estáticos com mutações; publicado em 2026-11-14.

## Travas de concorrência e limites

- [x] `POST entrada_mercadoria` com os produtos em ordem crescente de id pelo banco (item 2): `db.query produtos` com `sort = {id: "asc"}` dentro da transação, no lugar do `|sort:"id_produto":"int":false` em memória. Uma `precondition` confere a contagem, para que nenhum produto saia da nota sem erro. Contrato estático com mutações; publicado em 2026-11-14.
- [x] Teto de 50 itens na entrada (item 16): `precondition` antes da transação e `MAX_ITENS_ENTRADA` no DTO do Reflex, com a mesma mensagem. Desde 2026-11-14 o formulário também recusa a 51ª linha no "Adicionar item", com toast, como o balcão.
- [x] `PATCH motos/{id}` (item 13): preço e cor só mudam com a moto `DISPONIVEL`, e reenviar o valor atual é aceito. O status é conferido antes e de novo dentro da transação, depois da gravação que trava a linha. O Xano não tem `error_type` para 422; a recusa é `inputerror` (400), como as demais regras de negócio.
- [x] `POST produtos` com saldo 0 (item 14): `precondition` e gravação de `estoque_qtd : 0`; o formulário e o `ProdutoCreate` deixam de ter o saldo inicial.
- [x] `Financeiro/resumo_operacoes` com uma sessão de gerente (item 4), na parte de leitura. Em 2026-11-15 o resumo respondeu e o `ResumoFinanceiro` validou o retorno, tanto no mês corrente quanto nos últimos 360 dias. O período inválido recebeu 400.
- [ ] Ordem do `resumo_operacoes` (item 4). Não há como verificar ainda: produção tem 0 operações nos últimos 360 dias, e a documentação do `sort` continua contraditória. Ela chama o terceiro argumento de `asc` (`true` = crescente), o que tornaria o `false` decrescente, com o limite de 500 guardando as operações mais recentes. Mas o exemplo da própria doc, com `true`, devolve a lista decrescente. Conferir quando houver 2 ou mais operações no período.

## Testes de escrita e concorrência (pendente)

- [ ] Workspace ou branch de testes do Xano definido pelo usuário. Sem ele, estes testes não rodam: a escrita e a concorrência gravam dados reais, e o plano Free publica em produção.
- [ ] Cenários novos (item 17): duas entradas com o mesmo documento; duas entradas com produtos em ordens opostas; entrada e venda de balcão do mesmo produto.
- [ ] Rodar a integração com escrita e concorrência no workspace de testes, com `try`/`finally` nas variáveis (`docs/quality.md`), e registrar o resultado.

## Entregas publicadas

- [x] Entrega 1 (itens 9, 10, 11 e 13 a 16): revisão em 6 ciclos sem achado Alto ou Crítico; validador do MCP, `ruff`, `compileall`, `pytest` (448 aprovados e 44 ignorados), `reflex compile --dry` e `--dry-run` revisado. Push dos 7 arquivos em 2026-11-14, autorizado pelo usuário. A CLI listou "Unresolved References" para tabelas e funções existentes, aviso que não apareceu no `--dry-run`. Era falso positivo, porque com `-i` a CLI só resolve referências dentro dos arquivos filtrados: o `--dry-run` seguinte deu "No changes to push", e o VENDEDOR recebe 403 no `POST entrada_mercadoria` publicado.
- [x] Entrega 2 (itens 2 e 12: `balcao/vendas_POST.xs` e `entrada_mercadoria_POST.xs`), push em 2026-11-14 autorizado pelo usuário. O push trouxe de novo o falso positivo "Unresolved References"; o `--dry-run` seguinte deu "No changes to push". Ao vivo, `test_cart_with_a_nonexistent_product_is_refused_before_any_write` passa como VENDEDOR: um carrinho com produto inexistente recebe 400 "Produto inativo ou inexistente" antes da transação, sem gravar nada e sem depender de produto no banco (produção tem zero). Desde 2026-11-15, o teste também confere `status_code == 400`.
- [x] `docs/quality.md` com a referência de 2026-11-14.

## Banco e encerramento (pendente)

- [ ] Banco, conforme a decisão: `default_motos` (item 5), índice em `event_log.user_id` (item 7) e `motos.id_modelo` (item 8). O índice de `entrada_mercadoria` já existe (item 6).
- [ ] Push do banco (itens 5, 7 e 8), com `--dry-run` revisado e o OK do usuário.
- [ ] Docs: `docs/xano-api-client.md`, `docs/quality.md` e `docs/schema.sql`, se o banco mudar.
- [ ] Mover para o archive e commit (usuário).
