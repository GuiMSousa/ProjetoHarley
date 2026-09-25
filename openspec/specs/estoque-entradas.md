# Especificação: entradas de mercadoria e estoque

## Requisito: registro atômico de entrada

`POST entrada_mercadoria` DEVE receber cabeçalho (`id_fornecedor`, `numero_documento`) e itens (`id_produto`, `quantidade`, `valor_unitario`) e gravar, dentro de uma única `db.transaction`, o cabeçalho, os itens e o incremento de `produtos.estoque_qtd` de cada item.

### Cenário: registro bem-sucedido

- **DADO** um gerente autenticado, um fornecedor ativo e os produtos ativos P1 (estoque 3) e P2 (estoque 0)
- **QUANDO** registrar a entrada "NF-1" com P1 × 5 a 10,00 e P2 × 2 a 25,50
- **ENTÃO** P1 DEVE ficar com estoque 8 e P2 com estoque 2
- **E** `valor_total` DEVE ser 101,00

### Cenário: item inválido provoca rollback

- **DADO** uma entrada com um item válido e outro com produto inativo
- **QUANDO** o endpoint processar a entrada
- **ENTÃO** a resposta DEVE ser `400`
- **E** nenhum cabeçalho, item ou alteração de estoque DEVE ser persistido

## Requisito: validação de integridade

O Xano DEVE rejeitar com `400` e mensagem legível: fornecedor inexistente ou inativo, documento vazio, lista de itens vazia, produto repetido, produto inexistente ou inativo, `quantidade < 1` e `valor_unitario < 0.01`. O frontend DEVE aplicar as mesmas regras antes do envio.

### Cenário: valores não positivos

- **DADO** um item com `quantidade = 0` ou `valor_unitario <= 0`
- **QUANDO** o formulário for enviado
- **ENTÃO** o DTO DEVE rejeitar o envio localmente
- **E** o Xano DEVE rejeitar o mesmo payload se enviado diretamente

## Requisito: documento único por fornecedor

O par `(id_fornecedor, numero_documento)` DEVE ser único.

### Cenário: envio duplicado

- **DADO** uma entrada já registrada com `(fornecedor 3, "NF-1")`
- **QUANDO** outra entrada com o mesmo par for enviada
- **ENTÃO** ela DEVE ser rejeitada e o estoque NÃO DEVE ser incrementado novamente

## Requisito: autoria e totais do servidor

`id_funcionario` DEVE vir de `$auth.id → user.id_funcionario`; `valor_total` DEVE ser `Σ (quantidade × valor_unitario)`; `data_entrada` DEVE ser `now`. Valores equivalentes enviados pelo cliente DEVEM ser ignorados.

### Cenário: payload adulterado

- **DADO** um payload com `id_funcionario` de outro funcionário e `valor_total = 1`
- **QUANDO** a entrada for registrada
- **ENTÃO** o registro DEVE conter o funcionário autenticado e o total calculado

## Requisito: imutabilidade

Entradas e itens registrados NÃO DEVEM ser alterados ou removidos. `PUT`, `PATCH` e `DELETE entrada_mercadoria/{id}` e `POST`, `PUT`, `PATCH` e `DELETE itens_compra_estoque[/{id}]` DEVEM responder `403`.

## Requisito: saldo alterado só por movimentação

`PUT` e `PATCH produtos/{id}` NÃO DEVEM alterar `estoque_qtd`. O saldo inicial PODE ser informado em `POST produtos`.

### Cenário: saldo protegido

- **DADO** um produto com estoque 8
- **QUANDO** um gerente enviar `PATCH produtos/{id}` com `estoque_qtd = 100`
- **ENTÃO** o estoque DEVE permanecer 8

## Requisito: matriz de acesso

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Consultar histórico e detalhe de entradas | sim | sim | sim |
| Registrar entrada | sim | não | não |
| Consultar fornecedores | sim | não | não |

### Cenário: perfil sem permissão de registro

- **DADO** um vendedor ou mecânico autenticado
- **QUANDO** acessar `/estoque/entradas`
- **ENTÃO** DEVE ver o histórico e o detalhe, sem a ação "Nova entrada"
- **E** um `POST entrada_mercadoria` forjado DEVE receber `403`

## Requisito: sessão e rotas protegidas no Reflex

As rotas `/admin`, `/workshop`, `/cadastros/*` e `/estoque/entradas` DEVEM restaurar a sessão no `on_load` antes de carregar dados e DEVEM usar a matriz `ROUTE_ROLES` para decidir entre conteúdo, acesso negado ou tela de login.

### Cenário: recarga de página

- **DADO** um vendedor autenticado em `/cadastros/clientes`
- **QUANDO** recarregar a página
- **ENTÃO** a sessão DEVE ser restaurada e as ações de escrita DEVEM reaparecer

### Cenário: acesso direto proibido

- **DADO** um vendedor autenticado
- **QUANDO** acessar diretamente `/cadastros/funcionarios`
- **ENTÃO** DEVE ver acesso negado dentro do App Shell, sem chamada ao Xano

### Cenário: sem sessão

- **DADO** um navegador sem cookie de sessão
- **QUANDO** acessar `/estoque/entradas`
- **ENTÃO** DEVE ver a tela de login e nenhuma chamada autenticada DEVE ser feita
