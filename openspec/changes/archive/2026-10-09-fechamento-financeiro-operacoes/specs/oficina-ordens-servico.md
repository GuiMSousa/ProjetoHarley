# Delta de especificação: oficina e ordens de serviço

Alterações à spec `openspec/specs/oficina-ordens-servico.md`, a aplicar no arquivamento.

## MODIFICADO — Requisito: máquina de estados

Acrescentar: a transição para `CONCLUIDA` DEVE lançar a receita da OS em `transacoes` na mesma transação (spec `financeiro`, requisito "lançamento da OS na conclusão"); uma OS com total zero conclui sem lançamento. O cancelamento NÃO DEVE gerar transação.

## ADICIONADO — Requisito: faturamento visível na OS

O detalhe de uma OS `CONCLUIDA` DEVE mostrar "Faturada · transação #N · data" quando houver lançamento, ou "Concluída sem lançamento financeiro (total zero)." / "Concluída sem lançamento financeiro registrado." quando não houver. O painel de confirmação da conclusão DEVE avisar "O total de R$ X será lançado como receita de serviço." ou, com total zero, "Total zero: a OS será concluída sem lançamento."
