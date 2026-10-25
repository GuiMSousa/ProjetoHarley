# Delta de especificação: arquitetura e contratos

Alterações à spec `openspec/specs/arquitetura-e-contratos.md`, a aplicar no arquivamento.

## MODIFICADO — Requisito: dados financeiros restritos

`GET transacoes` e `GET transacoes/{id}` DEVEM exigir `GERENTE`. Lançamentos, correções e exclusões manuais (`POST transacoes`, `PUT`/`PATCH`/`DELETE transacoes/{id}`) DEVEM responder `403` para qualquer perfil: transações nascem somente das operações de negócio (venda de moto, conclusão de OS e lançamento retroativo) e são imutáveis (spec `financeiro`).

A frase "A Change 10 (`fechamento-financeiro-operacoes`) proposta torna as transações imutáveis." DEVE ser removida.

### Cenário: gerente tenta corrigir uma transação

- **DADO** um `GERENTE` autenticado
- **QUANDO** enviar `PATCH transacoes/{id}` com outro `valor_total`
- **ENTÃO** a resposta DEVE ser `403` "Transações são imutáveis." e a transação NÃO DEVE mudar

## MODIFICADO — Requisito: autoria imutável

A frase "Correções de transações (`PUT`/`PATCH`) NÃO DEVEM substituir o autor original, nem pelo payload nem por quem edita." DEVE ser substituída por: "Transações não têm correção manual; o autor é sempre o funcionário do JWT da operação que as criou."
