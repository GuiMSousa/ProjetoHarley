# Tarefas

## 0. Decisões e verificações prévias (antes do Apply)

- [x] Aprovar D1: baixa na inclusão, devolução na remoção e no cancelamento; a conclusão não movimenta o estoque.
- [x] Aprovar D2: serviço como `tipo_item = SERVICO` na mesma tabela, com relaxamento de `id_produto` via `--sync`.
- [x] Confirmar D3: a peça usa `preco_venda` como fotografia; o valor do serviço é informado por `GERENTE`/`MECANICO`.
- [x] Aprovar D4: produto repetido na OS é rejeitado.
- [x] Aprovar D5: remoção física com rastro no livro; o cancelamento mantém itens e totais.
- [x] Aprovar D6: `movimentacoes_estoque` com índice único `(id_produto, versao_anterior)` e `Estoque/movimentar_estoque`, também na entrada de mercadoria.
- [x] Aprovar D7: trava da linha da OS por `atualizado_em` antes de reler o status.
- [x] Aprovar D8: totais gravados na OS e recalculados a partir dos itens no detalhe.
- [x] Aprovar D9: rotas `POST ordens_servico/{id}/itens` e `DELETE ordens_servico/{id}/itens/{item_id}`; rotas legadas continuam `403`.
- [x] Aprovar D10: itens legados lidos como peça sem baixa.
- [x] Confirmar D11: qualquer `GERENTE`/`MECANICO` edita itens de qualquer OS editável.
- [x] No validador XanoScript, confirmar:
  - `function.run` dentro de `db.transaction`;
  - rota com dois parâmetros de caminho em `DELETE`;
  - `db.del`;
  - `|round:2`;
  - índice `btree|unique` composto.
- [ ] `$error.message` no `catch`: melhoria opcional não aplicada. Só é verificável no Xano real, e o `catch` usa a mensagem genérica de conflito, como previsto no design.
- [x] Confirmar a alternância Peça | Serviço (`rx.segmented_control`, inspecionado na versão instalada do Reflex, com `on_change` recebendo `str | list[str]`) e a lista de produtos clicável (`rx.button` em `rx.foreach`).

## 1. Xano — schema

- [x] `itens_ordem_servico`:
  - [x] tornar `id_produto` anulável;
  - [x] incluir `tipo_item`, `descricao`, `valor_unitario`, `estoque_baixado`, `id_funcionario` e `created_at`.
- [x] `ordens_servico`: incluir `valor_pecas`, `valor_servicos`, `valor_total` e `atualizado_em`.
- [x] `produtos`: incluir `versao_estoque`.
- [x] Criar `movimentacoes_estoque` com os índices `unique (id_produto, versao_anterior)`, `id_os` e `created_at desc`.

## 2. Xano — funções

- [x] Criar `Estoque/movimentar_estoque`: saldo, versão, livro e só depois o produto.
- [x] Criar `Oficina/totais_os`.
- [x] Alterar `Oficina/detalhe_os`: campos novos dos itens e totais vindos de `Oficina/totais_os`.

## 3. Xano — endpoints

- [x] Criar `ordens_servico/ordens_servico_id_itens_POST.xs`: pré-checagens, trava da OS, releitura, item, `SAIDA_OS`, totais e `try_catch`.
- [x] Criar `ordens_servico/ordens_servico_id_itens_item_id_DELETE.xs`: pré-checagens, trava, releitura, `ESTORNO_OS` condicional, `db.del`, totais e `try_catch`.
- [x] Alterar `ordens_servico/ordens_servico_id_status_POST.xs`:
  - [x] incluir `atualizado_em` em `$dados`;
  - [x] no cancelamento, devolver as peças baixadas depois do `patch`, em ordem de `id_produto`.
- [x] Alterar `entrada_mercadoria_POST.xs`:
  - [x] ordenar os itens por `id_produto`;
  - [x] trocar o `db.edit produtos` por `Estoque/movimentar_estoque(ENTRADA)`;
  - [x] manter a resposta e as mensagens.
- [x] Alterar `produtos/produtos_id_PATCH.xs` para descartar `versao_estoque`.
- [x] Atualizar a mensagem de bloqueio de `itens_ordem_servico_POST.xs` e de `itens_ordem_servico/itens_ordem_servico_id_{PUT,PATCH,DELETE}.xs`, preservando rotas e guids.
- [x] Validar todos os XanoScript (`node validate_xs.mjs xano`).

## 4. Python — DTOs e cliente

- [x] Em `services/ordens_servico.py`:
  - [x] criar `TipoItemOS` e `ItemOSCreate`;
  - [x] evoluir `ItemOrdemServico`, tolerando legado;
  - [x] incluir os totais em `OrdemServicoResumo` e `OrdemServicoDetalhe`.
- [x] No `XanoClient`: criar `adicionar_item_ordem_servico` e `remover_item_ordem_servico`.

## 5. Reflex

- [x] Em `workshop_state.py`:
  - [x] funções puras `can_edit_items`, `produto_row`, `filtrar_produtos`, `preview_item_total`, `build_item_payload` e `totais_row`;
  - [x] ajustar `item_row` e `os_row`, esta com o total;
  - [x] variáveis, variáveis computadas e eventos de catálogo, inclusão e remoção, com proteção contra reentrada, toasts e recarga depois de erro.
- [x] Em `workshop_pages.py`:
  - [x] criar `itens_section`, `custos_resumo` e `item_form`, com busca, saldo, preço e prévia;
  - [x] confirmação de remoção;
  - [x] coluna "Total" na lista;
  - [x] remover a nota "A inclusão de peças chega na próxima etapa".
- [x] Ocultar o formulário e as ações para `VENDEDOR` e para OS `CONCLUIDA`/`CANCELADA`.

## 6. Testes

- [x] `tests/test_ordens_servico.py`: DTOs de item e métodos novos do cliente.
- [x] `tests/test_workshop_state.py`: funções puras e eventos de itens.
- [x] `tests/test_ordens_servico_contracts.py`: inclusão, remoção, cancelamento com devolução e rotas legadas.
- [x] `tests/test_estoque_contracts.py`: entrada via `movimentar_estoque`, livro, índice único e `PATCH produtos`.
- [x] `tests/test_integration_xano.py`:
  - [x] cenários de leitura e `403`;
  - [x] ciclo de itens com escrita;
  - [x] concorrência opcional.
- [x] Atualizar os testes afetados pela mudança de contrato.

## 7. Verificação

- [x] `.venv/Scripts/python -m unittest discover -s tests`
- [x] `.venv/Scripts/python -m py_compile` em todos os módulos
- [x] `reflex compile --dry`
- [x] Validador XanoScript sem erros

## 8. Documentação e Archive

- [x] `docs/domain-model.md`: itens de OS, totais, livro de movimentações, regra de saldo e entrada via livro.
- [x] `docs/xano-api-client.md`: rotas novas, métodos do cliente, matriz e testes.
- [x] `openspec/specs/oficina-ordens-servico.md`: requisitos de itens, totais e cancelamento com devolução.
- [x] `openspec/specs/estoque-entradas.md`: livro de movimentações e serialização por versão.
- [x] Registrar em `proposal.md` o resultado aplicado, as notas de implementação e o status.
- [x] Mover para `openspec/archive/itens-os-baixa-estoque/`.

## Fora do repositório (usuário)

- [ ] `xano workspace push -d ./xano --sync --dry-run`, revisão e depois publicação, de preferência antes num branch.
- [ ] Suíte de integração com `XANO_TEST_*` e `XANO_TEST_ALLOW_WRITES=true`; concorrência com `XANO_TEST_CONCURRENCY=true`.
