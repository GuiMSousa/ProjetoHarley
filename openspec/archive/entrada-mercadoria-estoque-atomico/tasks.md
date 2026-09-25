# Tarefas

## 0. Decisões (antes do Apply)

- [x] Aprovar D1 — unicidade de `(id_fornecedor, numero_documento)`.
- [x] Aprovar D2 — bloqueio (e não remoção) das mutações diretas de entradas e itens.
- [x] Aprovar D3 — `estoque_qtd` fora da edição de produtos.
- [x] Aprovar D4 — estratégia de incremento e risco de concorrência.
- [x] Aprovar D5 — `data_entrada` definida pelo servidor.
- [x] Aprovar D6 — sem transação `COMPRA` nesta Change.
- [x] Aprovar D7 — restringir `GET fornecedores` a `GERENTE`.
- [x] Confirmar na documentação Xano a sintaxe de `db.transaction`, `foreach` e agregação (`isolation` rejeitado pelo validador; ver notas na proposta).

## 1. Xano — schema

- [x] Adicionar `numero_documento` (text `trim`, opcional na tabela) a `xano/table/entrada_mercadoria.xs`.
- [x] Adicionar `id_funcionario` (referência a `funcionarios`, opcional na tabela) a `entrada_mercadoria`.
- [x] Criar índice `btree|unique (id_fornecedor, numero_documento)` e `btree (id_funcionario)`.

## 2. Xano — endpoint transacional

- [x] Reescrever `xano/api/harley/entrada_mercadoria_POST.xs` com input explícito `{id_fornecedor, numero_documento, itens[]}` (sem `dblink`).
- [x] Aplicar `enforce_role` `GERENTE` e resolver `$auth_user.id_funcionario`.
- [x] Envolver validações e gravações em `db.transaction`.
- [x] Validar fornecedor existente e ativo.
- [x] Validar documento não vazio e não duplicado para o fornecedor.
- [x] Validar lista de itens não vazia e sem produto repetido.
- [x] Validar cada item: produto existente e ativo, `quantidade >= 1`, `valor_unitario >= 0.01`.
- [x] Gravar cabeçalho, itens e incremento de `produtos.estoque_qtd`.
- [x] Calcular e gravar `valor_total` no servidor.
- [x] Retornar `EntradaMercadoriaDetalhe`.
- [x] Escrever mensagens de `precondition` em português.

## 3. Xano — leitura, bloqueios e alinhamentos

- [x] `entrada_mercadoria_GET.xs`: `ALL`, ordenação decrescente por data e campos enriquecidos (`nome_fornecedor`, `nome_funcionario`, `quantidade_itens`).
- [x] `entrada_mercadoria_id_GET.xs`: `ALL`, cabeçalho enriquecido e itens com `codigo`, `nome_produto` e `valor_total_item`.
- [x] `itens_compra_estoque_GET.xs` e `itens_compra_estoque_id_GET.xs`: `ALL`.
- [x] Bloquear `entrada_mercadoria_id_PUT/PATCH/DELETE.xs` com rejeição explícita.
- [x] Bloquear `itens_compra_estoque_POST.xs` e `itens_compra_estoque_id_PUT/PATCH/DELETE.xs` com rejeição explícita.
- [x] `produtos_id_PATCH.xs` e `produtos_id_PUT.xs`: ignorar `estoque_qtd` (D3).
- [x] `fornecedores_GET.xs` e `fornecedores_id_GET.xs`: `GERENTE` (D7).
- [x] Validar sintaxe de todos os XanoScript alterados.

## 4. Python — DTOs e cliente

- [x] Criar `Projeto_HarleyStore/services/entradas.py` com `ItemEntradaCreate`, `EntradaMercadoriaCreate`, `EntradaMercadoriaResumo`, `ItemEntrada` e `EntradaMercadoriaDetalhe`.
- [x] Validar no DTO: itens não vazios, produto não repetido, `quantidade > 0`, `valor_unitario > 0`, documento não vazio após `strip`.
- [x] Remover `estoque_qtd` de `ProdutoUpdate` em `services/cadastros.py`.
- [x] Adicionar `list_entradas`, `get_entrada` e `registrar_entrada` ao `XanoClient`.
- [x] Mapear `400` para `XanoValidationError` e expor `message` segura em `400`/`422`.

## 5. Reflex — consistência de sessão e rotas

- [x] Criar `ROUTE_ROLES`, atualizar `role_allows_route` e criar `AuthState.allowed_routes` em `auth.py`.
- [x] Emitir toast em `load_user` somente quando houver erro.
- [x] Criar `guarded_page(content, route)` em `components.py` e mover `access_denied_page` para lá.
- [x] Reescrever `protected_page` de `/admin` e `/workshop` usando o guard.
- [x] Aplicar o guard a `cadastro_page` com a rota correspondente.
- [x] Encadear `on_load=[AuthState.restore_session, CadastrosState.load_*]` nas cinco rotas de cadastro.
- [x] Fazer `load_*` retornar sem chamar o Xano quando não houver sessão autenticada.
- [x] Exibir erro de carregamento da lista nas telas de cadastro.
- [x] Sidebar baseada em `allowed_routes`, com "Produtos e peças" visível ao vendedor e novo link "Entradas de mercadoria".
- [x] Exibir `estoque_qtd` no formulário de produto somente na criação.

## 6. Reflex — listagem compartilhada

- [x] Criar `Projeto_HarleyStore/listing.py` com `filter_rows`, `paginate`, `page_count`, `option_label` e `option_id`.
- [x] Refatorar `CadastrosState.visible_rows`, `total_pages` e o parse de `id_cliente` para usar `listing.py`, sem mudança de comportamento.

## 7. Reflex — entradas de mercadoria

- [x] Criar `Projeto_HarleyStore/entradas_state.py` com `EntradasState(AuthState)`.
- [x] Implementar carga do histórico com loading, erro, busca e paginação.
- [x] Implementar detalhe em modal com loading dedicado.
- [x] Implementar formulário mestre-detalhe: fornecedor, documento, adicionar/remover itens, editar item, total previsto.
- [x] Carregar opções de fornecedores e produtos ativos ao abrir o formulário.
- [x] Implementar `save_entrada` com validação local, bloqueio de reentrada e tratamento de `400`, `401`, `403` e transporte.
- [x] Criar `Projeto_HarleyStore/entradas_pages.py` com tabela, modal de detalhe e formulário no tema Harley.
- [x] Registrar a rota `/estoque/entradas` com guard e `on_load=[AuthState.restore_session, EntradasState.load_entradas]`.

## 8. Testes

- [x] `tests/test_entradas.py` — DTOs: quantidade `0`/negativa, preço `0`/negativo, itens vazios, produto repetido, documento em branco, payload válido; DTO de leitura com campos legados nulos.
- [x] `tests/test_entradas.py` — cliente: caminhos e métodos HTTP, payload sem `id_funcionario`/`valor_total`/`data_entrada`, parsing de resumo e detalhe, `400` → `XanoValidationError` com mensagem, `403` → `XanoPermissionError`.
- [x] `tests/test_entradas_state.py` — `can_register` por perfil, adicionar/remover item (mínimo de um), total previsto, bloqueio de reentrada, validação local sem chamada HTTP.
- [x] `tests/test_estoque_contracts.py` — contrato XanoScript: `db.transaction`, `enforce_role` `GERENTE`, `$auth_user.id_funcionario`, checagem de `ativo` de fornecedor e produto, ausência de `$input.valor_total` e `$input.id_funcionario`, incremento de `estoque_qtd`, bloqueio das mutações diretas, `GET` com `ALL`, `estoque_qtd` fora do `PATCH`/`PUT` de produtos, `fornecedores_GET` com `GERENTE`.
- [x] Ampliar testes de rota: `role_allows_route` para todas as rotas de `ROUTE_ROLES`, rota desconhecida negada.
- [x] Testes de `listing.py` e regressão dos testes de cadastros.
- [x] Ajustar `tests/test_cadastros.py` para a remoção de `estoque_qtd` de `ProdutoUpdate`.

## 9. Documentação

- [x] `docs/domain-model.md`: novos campos de entrada, total calculado, imutabilidade, saldo alterado só por movimentação.
- [x] `docs/xano-api-client.md`: DTOs e métodos de entradas, mapeamento de `400`.
- [x] `docs/xano-api-client.md` ou `docs/domain-model.md`: matriz de acesso atualizada.

## 10. Verificação e Archive

- [x] Executar `python -m unittest discover -s tests -v`.
- [x] Executar `python -m py_compile` nos arquivos alterados.
- [x] Executar `reflex compile --dry`.
- [x] Validar os XanoScript alterados.
- [ ] Executar o roteiro de cenários contra Xano real (pendente: sem `XANO_API_BASE_URL` e credenciais neste workspace).
- [x] Registrar a limitação da integração real na proposta.
- [x] Consolidar os requisitos aprovados em `openspec/specs/estoque-entradas.md`.
- [x] Preencher "Resultado aplicado" e "Status" na proposta e mover a Change para `openspec/archive/`.

## Arquivos previstos

| Área | Criar | Alterar |
| --- | --- | --- |
| Xano | — | `table/entrada_mercadoria.xs`; `api/harley/entrada_mercadoria_POST.xs`, `entrada_mercadoria_GET.xs`, `entrada_mercadoria/*_{GET,PUT,PATCH,DELETE}.xs`; `itens_compra_estoque_{GET,POST}.xs`, `itens_compra_estoque/*_{GET,PUT,PATCH,DELETE}.xs`; `produtos/produtos_id_{PATCH,PUT}.xs`; `fornecedores_GET.xs`, `fornecedores/fornecedores_id_GET.xs` |
| Serviços | `services/entradas.py` | `services/xano_client.py`, `services/cadastros.py` |
| Reflex | `listing.py`, `entradas_state.py`, `entradas_pages.py` | `auth.py`, `components.py`, `cadastros_state.py`, `cadastros_pages.py`, `Projeto_HarleyStore.py` |
| Testes | `test_entradas.py`, `test_entradas_state.py`, `test_estoque_contracts.py` | `test_authentication.py`, `test_cadastros.py`, `test_cadastros_state.py` |
| Docs | — | `docs/domain-model.md`, `docs/xano-api-client.md` |

Nenhum arquivo de implementação deve ser alterado durante a etapa Propose.
