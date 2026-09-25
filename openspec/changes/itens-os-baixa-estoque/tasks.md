# Tarefas

## 0. Decisões e verificações prévias (antes do Apply)

- [ ] Aprovar D1: baixa na inclusão, devolução na remoção e no cancelamento; a conclusão não movimenta o estoque.
- [ ] Aprovar D2: serviço como `tipo_item = SERVICO` na mesma tabela, com relaxamento de `id_produto` via `--sync`.
- [ ] Confirmar D3: a peça usa `preco_venda` como fotografia; o valor do serviço é informado por `GERENTE`/`MECANICO`.
- [ ] Aprovar D4: produto repetido na OS é rejeitado.
- [ ] Aprovar D5: remoção física com rastro no livro; o cancelamento mantém itens e totais.
- [ ] Aprovar D6: `movimentacoes_estoque` com índice único `(id_produto, versao_anterior)` e `Estoque/movimentar_estoque`, também na entrada de mercadoria.
- [ ] Aprovar D7: trava da linha da OS por `atualizado_em` antes de reler o status.
- [ ] Aprovar D8: totais gravados na OS e recalculados a partir dos itens no detalhe.
- [ ] Aprovar D9: rotas `POST ordens_servico/{id}/itens` e `DELETE ordens_servico/{id}/itens/{item_id}`; rotas legadas continuam `403`.
- [ ] Aprovar D10: itens legados lidos como peça sem baixa.
- [ ] Confirmar D11: qualquer `GERENTE`/`MECANICO` edita itens de qualquer OS editável.
- [ ] No validador XanoScript, confirmar:
  - `function.run` dentro de `db.transaction`;
  - rota com dois parâmetros de caminho em `DELETE`;
  - `db.del`;
  - `|round:2`;
  - índice `btree|unique` composto;
  - `$error.message` no `catch`.
- [ ] Na skill `reflex-docs`, confirmar os componentes da alternância Peça | Serviço e da lista de produtos clicável.

## 1. Xano — schema

- [ ] `itens_ordem_servico`:
  - [ ] tornar `id_produto` anulável;
  - [ ] incluir `tipo_item`, `descricao`, `valor_unitario`, `estoque_baixado`, `id_funcionario` e `created_at`.
- [ ] `ordens_servico`: incluir `valor_pecas`, `valor_servicos`, `valor_total` e `atualizado_em`.
- [ ] `produtos`: incluir `versao_estoque`.
- [ ] Criar `movimentacoes_estoque` com os índices `unique (id_produto, versao_anterior)`, `id_os` e `created_at desc`.

## 2. Xano — funções

- [ ] Criar `Estoque/movimentar_estoque`: saldo, versão, livro e só depois o produto.
- [ ] Criar `Oficina/totais_os`.
- [ ] Alterar `Oficina/detalhe_os`: campos novos dos itens e totais vindos de `Oficina/totais_os`.

## 3. Xano — endpoints

- [ ] Criar `ordens_servico/ordens_servico_id_itens_POST.xs`: pré-checagens, trava da OS, releitura, item, `SAIDA_OS`, totais e `try_catch`.
- [ ] Criar `ordens_servico/ordens_servico_id_itens_item_id_DELETE.xs`: pré-checagens, trava, releitura, `ESTORNO_OS` condicional, `db.del`, totais e `try_catch`.
- [ ] Alterar `ordens_servico/ordens_servico_id_status_POST.xs`:
  - [ ] incluir `atualizado_em` em `$dados`;
  - [ ] no cancelamento, devolver as peças baixadas depois do `patch`, em ordem de `id_produto`.
- [ ] Alterar `entrada_mercadoria_POST.xs`:
  - [ ] ordenar os itens por `id_produto`;
  - [ ] trocar o `db.edit produtos` por `Estoque/movimentar_estoque(ENTRADA)`;
  - [ ] manter a resposta e as mensagens.
- [ ] Alterar `produtos/produtos_id_PATCH.xs` para descartar `versao_estoque`.
- [ ] Atualizar a mensagem de bloqueio de `itens_ordem_servico_POST.xs` e de `itens_ordem_servico/itens_ordem_servico_id_{PUT,PATCH,DELETE}.xs`, preservando rotas e guids.
- [ ] Validar todos os XanoScript (`node validate_xs.mjs xano`).

## 4. Python — DTOs e cliente

- [ ] Em `services/ordens_servico.py`:
  - [ ] criar `TipoItemOS` e `ItemOSCreate`;
  - [ ] evoluir `ItemOrdemServico`, tolerando legado;
  - [ ] incluir os totais em `OrdemServicoResumo` e `OrdemServicoDetalhe`.
- [ ] No `XanoClient`: criar `adicionar_item_ordem_servico` e `remover_item_ordem_servico`.

## 5. Reflex

- [ ] Em `workshop_state.py`:
  - [ ] funções puras `can_edit_items`, `produto_row`, `filtrar_produtos`, `preview_item_total`, `build_item_payload` e `totais_row`;
  - [ ] ajustar `item_row` e `os_row`, esta com o total;
  - [ ] variáveis, variáveis computadas e eventos de catálogo, inclusão e remoção, com proteção contra reentrada, toasts e recarga depois de erro.
- [ ] Em `workshop_pages.py`:
  - [ ] criar `itens_section`, `custos_resumo` e `item_form`, com busca, saldo, preço e prévia;
  - [ ] confirmação de remoção;
  - [ ] coluna "Total" na lista;
  - [ ] remover a nota "A inclusão de peças chega na próxima etapa".
- [ ] Ocultar o formulário e as ações para `VENDEDOR` e para OS `CONCLUIDA`/`CANCELADA`.

## 6. Testes

- [ ] `tests/test_ordens_servico.py`: DTOs de item e métodos novos do cliente.
- [ ] `tests/test_workshop_state.py`: funções puras e eventos de itens.
- [ ] `tests/test_ordens_servico_contracts.py`: inclusão, remoção, cancelamento com devolução e rotas legadas.
- [ ] `tests/test_estoque_contracts.py`: entrada via `movimentar_estoque`, livro, índice único e `PATCH produtos`.
- [ ] `tests/test_integration_xano.py`:
  - [ ] cenários de leitura e `403`;
  - [ ] ciclo de itens com escrita;
  - [ ] concorrência opcional.
- [ ] Atualizar os testes afetados pela mudança de contrato.

## 7. Verificação

- [ ] `.venv/Scripts/python -m unittest discover -s tests`
- [ ] `.venv/Scripts/python -m py_compile` em todos os módulos
- [ ] `reflex compile --dry`
- [ ] Validador XanoScript sem erros

## 8. Documentação e Archive

- [ ] `docs/domain-model.md`: itens de OS, totais, livro de movimentações, regra de saldo e entrada via livro.
- [ ] `docs/xano-api-client.md`: rotas novas, métodos do cliente, matriz e testes.
- [ ] `openspec/specs/oficina-ordens-servico.md`: requisitos de itens, totais e cancelamento com devolução.
- [ ] `openspec/specs/estoque-entradas.md`: livro de movimentações e serialização por versão.
- [ ] Registrar em `proposal.md` o resultado aplicado, as notas de implementação e o status.
- [ ] Mover para `openspec/archive/itens-os-baixa-estoque/`.

## Fora do repositório (usuário)

- [ ] `xano workspace push -d ./xano --sync --dry-run`, revisão e depois publicação, de preferência antes num branch.
- [ ] Suíte de integração com `XANO_TEST_*` e `XANO_TEST_ALLOW_WRITES=true`; concorrência com `XANO_TEST_CONCURRENCY=true`.
