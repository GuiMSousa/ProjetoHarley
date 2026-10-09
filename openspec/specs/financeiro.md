# Especificação: financeiro

## Requisito: origem das transações

Transações DEVEM nascer somente das operações de negócio, com `valor_total > 0` e `id_funcionario` do usuário autenticado (`$auth.id → user.id_funcionario`), nunca do payload:

| Tipo | Operação de origem | Regra |
| --- | --- | --- |
| `MOTO` | `POST vender_moto` (`Vendas/vender_moto`) | Valor da venda, cliente comprador e moto do cliente criada na mesma transação (spec `catalogo-vendas-motos`). |
| `ORDEM_SERVICO` | Conclusão da OS (`POST ordens_servico/{id}/status`) | Requisito "lançamento da OS na conclusão". |
| `ORDEM_SERVICO` | `Financeiro/lancar_os_concluidas_legadas` | Requisito "lançamento retroativo". |

`PECAS`, `BALCAO` e `COMPRA` existem no domínio, mas nenhuma operação os grava. A entrada de mercadoria NÃO DEVE gerar transação `COMPRA`.

## Requisito: transações imutáveis

Transações DEVEM ser imutáveis. `POST transacoes`, `PUT`, `PATCH` e `DELETE transacoes/{id}` DEVEM responder `403` para qualquer perfil. As rotas bloqueadas DEVEM chamar `Quick Start/enforce_role` antes do bloqueio e preservar rota e `guid`. Correções serão feitas por estorno numa Change futura.

| Rota | Resposta |
| --- | --- |
| `POST transacoes` | `403` "Transações são registradas somente pelas operações de venda e de oficina." |
| `PUT` / `PATCH transacoes/{id}` | `403` "Transações são imutáveis." |
| `DELETE transacoes/{id}` | `403` "Exclusão física desabilitada: transações são registros financeiros permanentes." |

### Cenário: gerente tenta lançar uma transação manual

- **DADO** um `GERENTE` autenticado
- **QUANDO** enviar `POST transacoes`
- **ENTÃO** a resposta DEVE ser `403` "Transações são registradas somente pelas operações de venda e de oficina." e nada DEVE ser gravado

## Requisito: lançamento da OS na conclusão

A transição de uma OS para `CONCLUIDA` DEVE gravar, na mesma `db.transaction` da transição, uma transação `ORDEM_SERVICO` com:

- `valor_total` igual ao total recalculado dos itens (`Oficina/totais_os`);
- `id_os`;
- o cliente da OS (ou o dono da moto, em OS anteriores à Change 6);
- a moto do cliente;
- a data da conclusão;
- o `id_funcionario` de quem concluiu (JWT).

Uma OS com total zero DEVE concluir sem lançamento. Se o lançamento falhar, a OS NÃO DEVE mudar de status. O cancelamento NÃO DEVE gerar transação. O detalhe da OS DEVE informar `id_transacao` e `data_lancamento` (nulos sem lançamento).

### Cenário: conclusão com itens

- **DADO** uma OS `EM_ANDAMENTO` com R$ 450,00 em peças e R$ 800,00 em serviços
- **QUANDO** um mecânico a concluir
- **ENTÃO** DEVE existir exatamente uma transação `ORDEM_SERVICO` de R$ 1.250,00 com o `id_os` da OS e o mecânico como autor
- **E** o detalhe da OS DEVE mostrar "Faturada · transação #N"

### Cenário: conclusão sem valor

- **DADO** uma OS `EM_ANDAMENTO` sem itens
- **QUANDO** for concluída
- **ENTÃO** nenhuma transação DEVE ser gravada e o detalhe DEVE informar "Concluída sem lançamento financeiro (total zero)."

### Cenário: conclusões simultâneas

- **DADO** uma OS `EM_ANDAMENTO` com itens
- **QUANDO** dois funcionários a concluírem ao mesmo tempo
- **ENTÃO** exatamente uma transição DEVE ser aceita e DEVE existir um único lançamento para a OS

### Cenário: cancelamento

- **DADO** uma OS cancelada
- **ENTÃO** nenhuma transação DEVE ser gravada para ela

## Requisito: lançamento retroativo

A função `Financeiro/lancar_os_concluidas_legadas`, executada pelo Run & Debug com o id de um `GERENTE` ativo, DEVE lançar cada OS `CONCLUIDA` sem transação e com total maior que zero, com a data de encerramento (ou de abertura) e esse gerente como autor. Executá-la de novo NÃO DEVE duplicar lançamentos. Nenhum endpoint DEVE chamá-la.

### Cenário: segunda execução

- **DADO** que a função já lançou as OS concluídas antes da Change 10
- **QUANDO** for executada de novo
- **ENTÃO** nenhuma transação nova DEVE ser gravada

## Requisito: visão consolidada (`GET financeiro/resumo`)

`GET financeiro/resumo` (grupo `HARLEY`, `auth = "user"`, somente `GERENTE`) DEVE unir, num período, as transações (`transacoes.data_transacao`) e as entradas de mercadoria (`entrada_mercadoria.data_entrada`), sem gravar nada.

**Entrada (query string):** `inicio` e `fim`, timestamps em milissegundos, obrigatórios.

**Validação:**

- `fim < inicio`: `400` "O fim do período deve ser igual ou posterior ao início.";
- `fim − inicio` acima de 366 dias: `400` "O período pode ter no máximo 366 dias."

**Natureza por tipo:** `MOTO`, `ORDEM_SERVICO`, `PECAS` e `BALCAO` são `RECEITA`; `COMPRA` (transações antigas) e `ENTRADA_MERCADORIA` são `DESPESA`. Como as entradas não geram `COMPRA`, nada conta duas vezes.

**Resposta (`200`):**

| Campo | Conteúdo |
| --- | --- |
| `inicio`, `fim` | O período consultado. |
| `receitas`, `despesas`, `saldo` | Totais do período inteiro, com 2 casas; `saldo = receitas − despesas`. |
| `por_tipo` | `{tipo, natureza, quantidade, valor}` somente dos tipos com operações no período. |
| `operacoes` | As 500 operações mais recentes (data decrescente). Cada uma tem `origem` (`TRANSACAO` ou `ENTRADA`), `id`, `tipo`, `natureza`, `data`, `valor`, `contraparte` (cliente ou fornecedor), `funcionario`, `id_os`, `id_moto_cliente`, `modelo`, `placa`, `id_entrada` e `numero_documento` (nulos quando não se aplicam). |
| `total_operacoes` | Total de operações do período. |
| `truncado` | `true` quando `total_operacoes > 500`. |

### Cenário: mês com venda, serviço e compra

- **DADO** no mês uma venda de moto de R$ 185.000,00, uma OS faturada de R$ 1.250,00 e uma entrada de R$ 8.200,00
- **QUANDO** o gerente consultar o mês
- **ENTÃO** as receitas DEVEM ser R$ 186.250,00, as despesas R$ 8.200,00 e o saldo R$ 178.050,00

### Cenário: período inválido

- **DADO** um período de 1º/1/2025 a 2/1/2026
- **QUANDO** for consultado
- **ENTÃO** a resposta DEVE ser `400` "O período pode ter no máximo 366 dias."

### Cenário: período com mais de 500 operações

- **DADO** 620 operações no período
- **QUANDO** o gerente consultar o período
- **ENTÃO** `operacoes` DEVE trazer as 500 mais recentes, `total_operacoes` DEVE ser 620 e `truncado` DEVE ser `true`
- **E** os totais DEVEM considerar as 620 operações

## Requisito: tela `/financeiro`

A rota `/financeiro` DEVE ser exclusiva do `GERENTE` e aparecer na navegação em "Gestão → Financeiro" e como atalho no dashboard. A tela DEVE ter:

- **Período:** datas e atalhos "Este mês", "Mês anterior" e "Últimos 30 dias". O Reflex DEVE validar ordem e limite de 366 dias antes da chamada e enviar os limites do dia em UTC−3 fixo (00:00:00.000 do primeiro dia e 23:59:59.999 do último).
- **Cartões:** receitas, despesas e saldo; o saldo negativo DEVE ser destacado.
- **Totais por tipo.**
- **Operações:** filtro por tipo e busca locais, sem nova chamada ao Xano.
- **Aviso de lista truncada:** "Mostrando as N operações mais recentes de M; os totais cobrem o período inteiro."

Erros, `429` e sessão expirada DEVEM ser tratados como nas demais telas.

## Requisito: matriz de acesso

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Concluir OS (gera lançamento) | sim | não | sim |
| Consultar transações (`GET transacoes`, `GET transacoes/{id}`) | sim | não | não |
| Criar, editar ou excluir transação manualmente | não | não | não |
| Visão consolidada (`/financeiro`, `GET financeiro/resumo`) | sim | não | não |

### Cenário: vendedor tenta ver o financeiro

- **DADO** um `VENDEDOR` autenticado
- **QUANDO** chamar `GET financeiro/resumo` ou `GET transacoes`
- **ENTÃO** a resposta DEVE ser `403`
- **E** `/financeiro` NÃO DEVE aparecer na navegação dele
