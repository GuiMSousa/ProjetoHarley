# Especificação: financeiro (nova, Change 10)

A aplicar em `openspec/specs/financeiro.md` no arquivamento.

## Requisito: lançamento da OS na conclusão

A transição de uma OS para `CONCLUIDA` DEVE gravar, na mesma `db.transaction` da transição, uma transação `ORDEM_SERVICO` com `valor_total` igual ao total recalculado dos itens (`Oficina/totais_os`), `id_os`, cliente da OS (ou o dono da moto em OS anteriores à Change 6), moto do cliente, data da conclusão e `id_funcionario` de quem concluiu (JWT). Uma OS com total zero DEVE concluir sem lançamento. Se o lançamento falhar, a OS NÃO DEVE mudar de status. O detalhe da OS DEVE informar `id_transacao` e `data_lancamento` (nulos sem lançamento).

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

## Requisito: transações imutáveis

Transações DEVEM nascer somente das operações de negócio (venda de moto, conclusão de OS e o lançamento retroativo de OS concluídas). `POST transacoes`, `PUT`, `PATCH` e `DELETE transacoes/{id}` DEVEM responder `403` para qualquer perfil, preservando rota e `guid`. Correções serão feitas por estorno numa Change futura.

### Cenário: gerente tenta lançar uma transação manual

- **DADO** um `GERENTE` autenticado
- **QUANDO** enviar `POST transacoes`
- **ENTÃO** a resposta DEVE ser `403` "Transações são registradas somente pelas operações de venda e de oficina." e nada DEVE ser gravado

## Requisito: visão consolidada

`GET financeiro/resumo` (somente `GERENTE`) DEVE receber `inicio` e `fim` em milissegundos e responder `400` quando `fim < inicio` ou quando o período passar de 366 dias. A resposta DEVE unir as transações do período (receitas, e `COMPRA` antigas como despesa) e as entradas de mercadoria do período (despesas), com `receitas`, `despesas`, `saldo = receitas − despesas`, totais por tipo, as 500 operações mais recentes, `total_operacoes` e `truncado`. Os totais DEVEM cobrir o período inteiro. As entradas NÃO DEVEM gerar transação `COMPRA`. O endpoint NÃO DEVE gravar nada.

### Cenário: mês com venda, serviço e compra

- **DADO** no mês uma venda de moto de R$ 185.000,00, uma OS faturada de R$ 1.250,00 e uma entrada de R$ 8.200,00
- **QUANDO** o gerente consultar o mês
- **ENTÃO** as receitas DEVEM ser R$ 186.250,00, as despesas R$ 8.200,00 e o saldo R$ 178.050,00

### Cenário: período inválido

- **DADO** um período de 1º/1/2025 a 2/1/2026
- **QUANDO** for consultado
- **ENTÃO** a resposta DEVE ser `400` "O período pode ter no máximo 366 dias."

## Requisito: lançamento retroativo

A função `Financeiro/lancar_os_concluidas_legadas`, executada uma vez pelo Run & Debug com o id de um `GERENTE` ativo, DEVE lançar cada OS `CONCLUIDA` sem transação e com total maior que zero, com a data de encerramento (ou de abertura). Executá-la de novo NÃO DEVE duplicar lançamentos. Nenhum endpoint DEVE chamá-la.

## Requisito: tela `/financeiro`

A rota `/financeiro` DEVE ser exclusiva do `GERENTE` e aparecer na navegação em "Gestão → Financeiro" e como atalho no dashboard. A tela DEVE ter período (datas e atalhos "Este mês", "Mês anterior" e "Últimos 30 dias", com limites do dia em UTC−3), cartões de receitas, despesas e saldo (saldo negativo destacado), totais por tipo e a lista de operações com filtro por tipo e busca locais (sem nova chamada ao Xano) e o aviso de lista truncada.

## Requisito: matriz de acesso

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Concluir OS (gera lançamento) | sim | não | sim |
| Consultar transações | sim | não | não |
| Criar, editar ou excluir transação manualmente | não | não | não |
| Visão consolidada (`/financeiro`, `GET financeiro/resumo`) | sim | não | não |
