# Especificação: venda de balcão de peças

## Requisito: venda atômica

`POST balcao/vendas` (grupo `HARLEY`, `auth = "user"`, `GERENTE` ou `VENDEDOR`) DEVE receber `chave_venda`, `id_cliente` opcional, `total_esperado` e de 1 a 30 itens (`id_produto` sem repetição e `quantidade` inteira maior que zero). Numa única `db.transaction`, DEVE gravar:

- a transação `BALCAO`, com `id_funcionario` do JWT, o cliente (ou nulo, para consumidor final) e o total dos itens;
- os itens em `itens_transacao`, com `valor_unitario` igual a `produtos.preco_venda` lido pelo Xano e `valor_total_item = quantidade × valor_unitario`;
- uma saída `SAIDA_VENDA` por item, pelo `Estoque/movimentar_estoque`, com o `id_transacao`.

Os produtos DEVEM ser gravados em ordem crescente de id, a mesma do cancelamento de OS. Qualquer falha DEVE desfazer tudo. A resposta DEVE ser o recibo: transação, nomes do cliente e do vendedor e itens com código e nome do produto.

### Cenário: venda com cliente

- **DADO** os produtos Filtro (R$ 89,90) e Pastilha (R$ 209,90) com saldo e uma cliente ativa
- **QUANDO** um vendedor vender 2 × Filtro e 1 × Pastilha a ela
- **ENTÃO** DEVE existir uma transação `BALCAO` de R$ 389,70 com a cliente e o vendedor
- **E** dois itens com o preço fotografado e duas saídas `SAIDA_VENDA` com o `id_transacao`
- **E** o saldo dos dois produtos DEVE diminuir

### Cenário: consumidor final

- **DADO** um carrinho sem cliente
- **QUANDO** a venda for fechada
- **ENTÃO** `id_cliente` DEVE ser nulo e o `/financeiro` DEVE mostrar "Consumidor final"

## Requisito: validações antes da gravação

Antes da transação, o Xano DEVE responder `400`, sem gravar nada, para: nenhum item, mais de 30 itens, produto repetido, produto inativo ou inexistente, cliente inativo ou inexistente, saldo insuficiente ("Saldo insuficiente para {codigo}: disponível {n}, solicitado {m}.") e total recalculado diferente de `total_esperado` ("Os preços mudaram desde que o carrinho foi montado: o total agora é R$ {total}. Revise o carrinho."). Dentro da transação, preços e saldos DEVEM ser conferidos de novo; uma divergência por corrida DEVE desfazer tudo com "A venda não foi registrada: o estoque ou os preços mudaram durante o fechamento. Revise o carrinho e tente novamente."

### Cenário: saldo insuficiente

- **DADO** o produto FLT0001 com saldo 3
- **QUANDO** o carrinho pedir 5 unidades
- **ENTÃO** a resposta DEVE ser `400` "Saldo insuficiente para FLT0001: disponível 3, solicitado 5." e nada DEVE ser gravado

### Cenário: preço alterado

- **DADO** um carrinho montado antes de o gerente mudar o preço de um produto
- **QUANDO** a venda for fechada com o total antigo
- **ENTÃO** a resposta DEVE ser `400` com o novo total e nada DEVE ser gravado

## Requisito: uma venda por carrinho

`chave_venda` (UUID gerado pelo Reflex por carrinho) DEVE ser gravada em cada item, com índice único `(chave_venda, id_produto)`. Repetir uma chave já gravada DEVE devolver o recibo da venda existente, sem nova baixa nem nova receita. O Reflex DEVE manter a chave nas novas tentativas e renová-la só depois de uma venda concluída ou ao limpar o carrinho.

### Cenário: resposta perdida e novo clique

- **DADO** uma venda gravada cuja resposta não chegou ao Reflex
- **QUANDO** o vendedor confirmar de novo o mesmo carrinho
- **ENTÃO** a resposta DEVE ser o recibo da mesma transação e o saldo DEVE ter baixado uma única vez

### Cenário: disputa pelo saldo

- **DADO** um produto com saldo N
- **QUANDO** duas vendas pedirem N unidades ao mesmo tempo
- **ENTÃO** exatamente uma DEVE ser aceita, a outra DEVE receber `400` e o saldo final DEVE ser 0

## Requisito: tela `/balcao`

A rota `/balcao` DEVE ser exclusiva de `GERENTE` e `VENDEDOR` e aparecer na navegação em "Vendas → Balcão" e como atalho no dashboard. A tela DEVE ter:

- **Peças:** filtro por categoria e busca local por código ou nome (até 20 resultados, com aviso para refinar); produto sem saldo aparece desativado como "Sem saldo".
- **Carrinho:** quantidade editável e remoção; adicionar o mesmo produto soma a quantidade; a quantidade NÃO DEVE passar do saldo carregado nem o carrinho de 30 produtos.
- **Cliente:** opcional, com "Consumidor final" como padrão.
- **Fechamento:** confirmação com itens, cliente e total; o botão DEVE travar durante o envio, com `yield` antes da chamada ao Xano, e um segundo clique NÃO DEVE gerar outra venda.
- **Recibo:** número, data, cliente, vendedor, itens e total; depois dele o carrinho é limpo e os saldos recarregados.
- **Erros:** saldo, preço ou conflito mantêm o carrinho e a chave e recarregam os produtos.

## Requisito: matriz de acesso

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Vender no balcão (`/balcao`, `POST balcao/vendas`) | sim | sim | não |
| Ver as vendas no balcão (`/financeiro`) | sim | não | não |
