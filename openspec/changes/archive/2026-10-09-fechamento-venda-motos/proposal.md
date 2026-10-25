# Proposta: fechamento de vendas de motos e transações financeiras (Change 9)

## Contexto

A Change 8 entregou o catálogo, as unidades em estoque (`motos`) e o ciclo de reserva em `/vendas`, com transições versionadas por `Vendas/transicionar_moto`. A conclusão da venda ficou explicitamente para esta Change (spec `catalogo-vendas-motos`).

Depois da Change 8, o backend da venda já foi escrito no Xano:

- `POST vender_moto` (grupo `HARLEY`, `auth = "user"`) resolve o funcionário pelo JWT e chama `Vendas/vender_moto`;
- `Vendas/vender_moto` valida a unidade, cria a moto do cliente (`motos_clientes`), registra a transação `MOTO` (`transacoes`) e passa a unidade a `VENDIDA` numa única `db.transaction`.

Faltam o contrato documentado, o método no `XanoClient`, a tela de fechamento em `/vendas` e os testes.

## Problema

1. O vendedor não consegue concluir uma venda pela aplicação: o endpoint existe, mas não há DTO, cliente nem tela.
2. O backend exige placa, mas uma moto 0 km sai da loja sem placa (o emplacamento vem depois). A tabela `motos_clientes` também exige placa.
3. A moto do cliente criada pela venda recebe `motos.modelo`, campo legado que é nulo nas unidades da Change 8; o nome real está em `modelos_moto.nome_modelo`.
4. Dois vendedores podem tentar vender a mesma unidade ao mesmo tempo; a tela precisa refletir o novo status sem deixar o usuário num formulário obsoleto.

## Objetivo

- Documentar o contrato de `POST /api:harley/vender_moto` (entradas, saída, regras e erros).
- Tornar a placa opcional na venda e em `motos_clientes`, mantendo a unicidade quando informada.
- Gravar o nome do modelo comercial na moto do cliente.
- Adicionar `XanoClient.vender_moto` com DTOs de entrada e de resposta.
- Adicionar em `/vendas` a ação "Vender" e o modal de fechamento, com validações, tratamento de concorrência e atualização da lista e do cache da vitrine.
- Cobrir cliente, DTOs, estado e contratos com testes.

## Decisões de negócio

- **D1 — Placa opcional:** a placa é opcional na venda e em `motos_clientes` (moto 0 km). Quando informada, continua única. Texto vazio vale como ausente.
- **D2 — Valor mínimo:** `valor_venda` deve ser maior que zero (mínimo R$ 0,01, com até duas casas decimais), igual ao Xano. O formulário vem preenchido com o preço da unidade e o vendedor pode negociar livremente.
- **D3 — Quem vende:** `VENDEDOR` ou `GERENTE` (`enforce_role VENDEDOR`). O funcionário vem sempre do JWT, nunca do payload.
- **D4 — Unidade reservada:** só pode ser vendida ao cliente da reserva; na tela, o cliente vem fixado. A unidade disponível pode ser vendida a qualquer cliente ativo.
- **D5 — Estado final:** `VENDIDA` é final; não há estorno nesta Change.
- **D6 — Nome do modelo:** a moto do cliente recebe `modelos_moto.nome_modelo`; unidades legadas mantêm `modelo`/`marca`.
- **D7 — Concorrência:** quando o Xano recusar a venda (vendida, reservada para outro cliente ou alterada por outro usuário), a tela recarrega a lista; se a unidade deixou de estar vendável, o modal fecha e a mensagem do Xano aparece em notificação.
- **D8 — Vitrine:** uma venda concluída invalida o cache de 60 s do catálogo, para a vitrine deixar de contar a unidade.

## Escopo

- `xano/table/motos_clientes.xs`: `placa` anulável.
- `xano/api/harley/vender_moto_POST.xs` e `xano/function/vendas/vender_moto.xs`: placa opcional, checagem de placa só quando informada e nome do modelo comercial.
- `Projeto_HarleyStore/services/motos.py`: `VendaMotoCreate` e `VendaMotoResultado`.
- `Projeto_HarleyStore/services/xano_client.py`: `vender_moto`.
- `Projeto_HarleyStore/services/cadastros.py` e `cadastros_state.py`: placa opcional nas motos de clientes.
- `Projeto_HarleyStore/vendas_state.py` e `vendas_pages.py`: ação "Vender", modal, validações, concorrência e atualização.
- Testes em `tests/` e documentação em `docs/`.

## Fora do escopo

- Estorno ou cancelamento de venda; `VENDIDA` continua final.
- Redesenho de `transacoes` (itens, forma de pagamento, parcelas, nota fiscal) e telas de consulta financeira.
- Regra de desconto máximo ou piso de preço.
- Emplacamento e documentação do veículo após a venda (a placa pode ser preenchida depois em Cadastros → Motos de clientes).
- Comissão de vendedor.
