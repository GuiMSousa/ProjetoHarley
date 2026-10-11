# Proposta: venda de balcão de peças (Change 11)

## Contexto

A venda no balcão é um dos três fluxos de receita do projeto. `docs/project-overview.md` §3 e o relatório do projeto (PDF) pedem para "unificar o controle de vendas no balcão, vendas de motocicletas e prestação de serviços mecânicos"; os dois outros fluxos já existem. As Changes anteriores deixaram a venda no balcão explicitamente para esta Change:

- **Change 10, D1:** "Venda no balcão vai para a Change 11, que reutilizará o resumo." O balcão exige itens de transação e um novo tipo de movimentação de estoque.
- **`docs/domain-model.md` → *Transacoes*:** "transações não possuem linhas de itens; a venda no balcão (`BALCAO`/`PECAS`) com baixa de estoque depende de uma decisão de modelagem e fica para a Change 11."
- **`docs/project-overview.md` §9 e relatório:** "A integridade do estoque deve ser priorizada durante a baixa via OS ou Vendas no Balcão."
- **`Lojas_HarleyDavidson.pdf`:** as saídas de estoque "podem ocorrer através de vendas realizadas no balcão ou pela utilização de produtos e peças em ordens de serviço"; os vendedores "são responsáveis pelas vendas realizadas no balcão".

Estado atual confirmado no código:

- `transacoes` já aceita `PECAS` e `BALCAO`, mas nenhuma operação os grava. Desde a Change 10, transações nascem só de operações de negócio; o CRUD manual responde `403`.
- O resumo financeiro (`Financeiro/resumo_operacoes`) já classifica `PECAS` e `BALCAO` como receita.
- O estoque só muda por `Estoque/movimentar_estoque`, cujo livro conhece `ENTRADA`, `SAIDA_OS` e `ESTORNO_OS`.
- O Reflex não tem tela de balcão. O vendedor só vende motos (`/vendas`).

## Problema

A loja não consegue registrar uma venda de peças no balcão:

- não há onde guardar os itens vendidos;
- a saída do estoque não acontece, e o saldo só bate se alguém ajustar o produto por fora;
- a receita não aparece no resumo financeiro.

## Objetivo

Permitir que vendedor e gerente vendam peças do estoque a um cliente identificado ou a um consumidor final. A venda grava, numa única operação atômica:

- a transação `BALCAO`;
- os itens vendidos;
- a baixa de estoque de cada item.

A receita passa a aparecer no resumo financeiro sem nenhuma mudança nele.

## Regras de negócio

- **Itens:**
  - de 1 a 30 itens por venda;
  - cada produto aparece uma única vez, com quantidade inteira maior que zero;
  - só entram produtos ativos.
- **Preço:** é a fotografia de `produtos.preco_venda` no fechamento, lida pelo Xano. O payload não traz preço; `valor_total_item = quantidade × valor_unitario` e `valor_total` é a soma dos itens. Não há desconto.
- **Total conferido:** o Reflex envia o total que mostrou ao vendedor (`total_esperado`). Se o total recalculado pelo Xano for diferente (um preço mudou), a venda é recusada sem gravar nada e o vendedor revisa o carrinho.
- **Estoque:**
  - cada item gera uma saída `SAIDA_VENDA` no livro de movimentações, ligada à transação;
  - uma venda acima do saldo é recusada por inteiro, com a mensagem do produto em falta;
  - o carrinho não reserva estoque.
- **Atomicidade:** transação, itens e baixas são gravados juntos. Qualquer falha desfaz tudo.
- **Uma venda por carrinho:** cada carrinho tem uma chave (`chave_venda`, UUID gerado pelo Reflex). Repetir a mesma chave devolve a venda já registrada, sem nova baixa nem nova receita. Isso protege contra a resposta perdida por timeout seguida de novo clique.
- **Cliente:** opcional. Sem cliente, a venda é de consumidor final; com cliente, ele deve estar ativo.
- **Autoria:** `id_funcionario` vem do usuário autenticado (JWT → `user.id_funcionario`), nunca do payload.
- **Imutabilidade:** a venda não tem edição nem exclusão; os itens não têm rotas genéricas. Estorno e devolução ficam para uma Change futura, como já previsto na Change 10 (D5).
- **Acesso:**
  - `GERENTE` e `VENDEDOR` vendem no balcão;
  - `MECANICO` não vende, porque as peças dele saem pela OS;
  - a consulta das vendas continua no `/financeiro`, só para o `GERENTE`.

## Escopo

### Xano

- **Tabela nova `itens_transacao`:** produto, quantidade, preço fotografado, total do item e chave da venda. Tem índice único `(chave_venda, id_produto)`.
- **`movimentacoes_estoque`:**
  - tipo novo `SAIDA_VENDA`;
  - campo `id_transacao`, anulável e com índice.
- **`Estoque/movimentar_estoque`:** aceita `SAIDA_VENDA`, que subtrai do saldo e exige produto ativo, e grava `id_transacao`.
- **Endpoint novo `POST balcao/vendas`:** valida tudo, grava de forma atômica e responde o recibo da venda.
- **Função nova `Balcao/detalhe_venda`:** monta o recibo (transação, cliente, funcionário e itens com código e nome do produto).

### Python

- DTOs em `Projeto_HarleyStore/services/balcao.py`.
- `XanoClient.vender_balcao`.

### Reflex

- **Página nova `/balcao` (`GERENTE` e `VENDEDOR`):**
  - busca de peças com saldo e preço;
  - carrinho com quantidade editável, subtotal e remoção;
  - seleção opcional de cliente ("Consumidor final" por padrão);
  - total;
  - confirmação, fechamento e recibo.
- **Shell:** rota em `ROUTE_ROLES`, item "Venda no balcão" na seção "Vendas" da navegação e atalho no dashboard.
- **Financeiro:** a descrição das operações `BALCAO` passa a "Venda no balcão #N"; sem cliente, a contraparte aparece como "Consumidor final".

### Testes e documentação

- **Testes:**
  - contratos XanoScript;
  - DTOs e cliente HTTP;
  - funções puras e eventos do estado do balcão;
  - integração com o Xano real (marcadores `integration`, `writes` e `concurrency`).
- **Documentação:** `docs/domain-model.md`, `docs/xano-api-client.md` e `docs/project-structure.md`.
- **Specs:**
  - nova `openspec/specs/vendas-balcao.md`;
  - deltas em `estoque-entradas.md`, `financeiro.md` e `arquitetura-e-contratos.md`.

## Impacto

| Módulo | Impacto |
| --- | --- |
| Transações / Financeiro | Itens de transação; nova origem de receita `BALCAO`; descrição no `/financeiro`. O resumo do Xano não muda. |
| Estoque | Novo tipo de saída e origem no livro; `movimentar_estoque` ampliada sem mudar o comportamento dos tipos atuais. |
| Cadastros | Somente leitura: produtos e clientes alimentam a tela. |
| Oficina | Nenhuma mudança: `SAIDA_OS` e `ESTORNO_OS` continuam iguais. |
| Shell, autenticação e dashboard | Rota `/balcao`, item de navegação e atalho. |

## Matriz de acesso (alterações)

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Vender no balcão (`/balcao`, `POST balcao/vendas`) | sim | sim | não |
| Ver as vendas no balcão (`/financeiro`) | sim | não | não |

## Fora do escopo

- Estorno, cancelamento, devolução e troca de venda.
- Desconto, preço negociado e alteração de preço no carrinho.
- Forma de pagamento, troco, caixa, parcelas e nota ou cupom fiscal.
- Vínculo da venda com uma moto do cliente.
- Listagem e detalhe das vendas para o vendedor; detalhe dos itens dentro do `/financeiro`.
- Uso automático do tipo `PECAS` (D1).
- Venda de serviços no balcão.
- Reserva de estoque durante a montagem do carrinho.

## Critérios de aceite

- **Venda com cliente:** vender 2 × Filtro (R$ 89,90) e 1 × Pastilha (R$ 209,90) a uma cliente ativa:
  - cria uma transação `BALCAO` de R$ 389,70, com a cliente e o vendedor do JWT;
  - cria 2 itens com o preço fotografado;
  - cria 2 saídas `SAIDA_VENDA` com o `id_transacao`;
  - reduz o saldo dos dois produtos.
- **Consumidor final:** a venda sem cliente grava `id_cliente` nulo, e o `/financeiro` mostra "Consumidor final".
- **Saldo insuficiente:** pedir 5 unidades de um produto com saldo 3 responde `400` "Saldo insuficiente para FLT-0001: disponível 3, solicitado 5." e não grava nada.
- **Preço alterado:** se o gerente mudar um preço depois que o carrinho foi montado, o fechamento responde `400`, informa o novo total e não grava nada.
- **Repetição:** reenviar a mesma `chave_venda` devolve a mesma venda, sem segunda transação nem segunda baixa.
- **Concorrência:** duas vendas simultâneas da última unidade de um produto resultam em uma venda aceita e uma recusada, e o saldo final é zero.
- **Validação:** carrinho vazio, mais de 30 itens, produto repetido, produto inativo e cliente inativo respondem `400` sem gravar.
- **Acesso:**
  - `MECANICO` recebe `403` em `POST balcao/vendas` e não vê `/balcao`;
  - `VENDEDOR` vende, mas continua sem acesso ao `/financeiro`.
- **UI:**
  - o carrinho soma a quantidade quando o mesmo produto é adicionado de novo;
  - o carrinho impede quantidade acima do saldo carregado;
  - o botão fica travado durante o envio;
  - depois da venda, o recibo aparece, o carrinho é limpo e o saldo dos produtos é recarregado;
  - a tela funciona em 500 px.
- **Verificação antes do Archive:** suíte automatizada, `py_compile`, `reflex compile --dry`, validador XanoScript e `--dry-run` do push executados.

## Dependências

- **Change 10 publicada no Xano:** a venda grava em `transacoes`, que já é imutável, e aparece em `Financeiro/resumo_operacoes`.
- **Pendência do arquivamento da Change 10 (P0), resolvida em 2026-10-09:** `openspec/specs/financeiro.md` foi criada e os deltas foram aplicados em `arquitetura-e-contratos.md` e `oficina-ordens-servico.md`. Os deltas desta Change partem dessas specs.
- **Débito 1 da auditoria:** a integração com escrita e concorrência ainda não rodou contra o Xano real. Esta Change acrescenta cenários a ela.

## Decisões aprovadas (2026-10-09)

Detalhadas em `design.md` §3.

- **P0 (concluída):** deltas de spec pendentes da Change 10 aplicados.
- **D1:** tipo `BALCAO` para toda venda de balcão; `PECAS` sem uso automático.
- **D2:** itens em tabela nova `itens_transacao`, ligada à própria transação.
- **D3:** preço fotografado pelo Xano no fechamento, sem desconto.
- **D4:** total conferido (`total_esperado`).
- **D5:** idempotência por `chave_venda`.
- **D6:** saída `SAIDA_VENDA` pelo livro, com saldo verificado antes e dentro da transação.
- **D7:** cliente opcional (consumidor final).
- **D8:** acesso de `GERENTE` e `VENDEDOR`; sem endpoint de consulta nesta Change.
- **D9:** de 1 a 30 itens por venda.
- **D10:** deploy com ampliação de enum, que pode exigir `--sync`.

## Status

Arquivada em 2026-10-11: implementada, publicada e com as specs aplicadas (`vendas-balcao.md` nova; deltas em `financeiro.md`, `estoque-entradas.md` e `arquitetura-e-contratos.md`).
