# Proposta: fechamento financeiro e visão consolidada das operações (Change 10)

## Contexto

As Changes 1 a 9 entregaram cadastros, entrada de mercadoria com livro de estoque, oficina com máquina de estados e itens, catálogo, reservas e a venda de motos. Três pendências foram adiadas, uma a uma, para uma "Change de fechamento financeiro":

- **Change 5:** a entrada de mercadoria não gera transação `COMPRA` (D6).
- **Change 7:** concluir uma OS não lança a transação `ORDEM_SERVICO`.
- **Auditoria, débito 3 (prioridade alta):** `transacoes` deve ser imutável, com valores calculados no servidor. A Change 9 também o deixou fora do escopo, junto com as telas de consulta financeira.

Além disso, a visão consolidada `vw_resumo_operacoes`, que une transações e entradas de mercadoria, é objetivo do projeto (`docs/project-overview.md` e `docs/domain-model.md`) e ainda não existe.

Estado atual:

- `transacoes` é um CRUD genérico. O saneamento pós-Change 9 restringiu a leitura e os lançamentos e correções manuais ao `GERENTE` e preservou o autor no `PUT`, mas tipo, valor e data ainda vêm do payload. Só o `DELETE` está bloqueado.
- A única transação gerada por regra de negócio é a `MOTO`, da venda (Change 9).
- O Reflex não consulta transações e não tem tela financeira.

## Problema

1. O faturamento da oficina não é registrado: uma OS concluída não aparece no financeiro.
2. Os registros financeiros não são confiáveis: qualquer vendedor pode criar, alterar o valor ou mudar o tipo de uma transação, e todos os perfis leem os dados financeiros.
3. O gerente não tem como ver receitas, despesas e saldo de um período.

## Objetivo

- Lançar automaticamente a receita da OS na conclusão, na mesma transação da mudança de status.
- Tornar `transacoes` imutável e restrita a lançamentos feitos pelas operações de negócio.
- Entregar ao `GERENTE` a visão consolidada de receitas (transações) e despesas (entradas de mercadoria) por período, com totais por tipo e saldo.
- Lançar retroativamente as OS concluídas antes desta Change.

## Regras de negócio

- **Lançamento da OS:** a transição para `CONCLUIDA` grava uma transação `ORDEM_SERVICO` com:
  - o total da OS recalculado a partir dos itens;
  - o cliente e a moto da OS;
  - o funcionário que concluiu (JWT);
  - o vínculo `id_os`.

  Uma OS com total zero (garantia, cortesia) é concluída sem lançamento. Se o lançamento falhar, a OS não muda de status.
- **Um lançamento por OS:** garantido pela máquina de estados, porque a OS sai de `EM_ANDAMENTO` uma única vez.
- **Imutabilidade:** transações nascem somente da venda de moto e da conclusão de OS. Criação, edição e exclusão manuais respondem `403`; correções serão feitas por estorno numa Change futura.
- **Visão consolidada:**
  - natureza por tipo:
    - receitas: `MOTO`, `ORDEM_SERVICO`, `PECAS` e `BALCAO`;
    - despesas: entradas de mercadoria e transações `COMPRA` antigas;
  - saldo = receitas − despesas;
  - período obrigatório de até 366 dias;
  - os totais cobrem o período inteiro, e a lista traz as 500 operações mais recentes.
- **Sem dupla contagem:** as entradas de mercadoria não geram transação `COMPRA`; a visão as lê diretamente.
- **Acesso:** somente o `GERENTE` consulta transações e a visão consolidada.

## Escopo

### Xano

- `transacoes`: campo `id_os` (anulável) e índice `btree` simples.
- `POST ordens_servico/{id}/status`: lançamento `ORDEM_SERVICO` na conclusão, dentro da `db.transaction`.
- `Oficina/detalhe_os`: `id_transacao` e `data_lancamento` da OS.
- CRUD de `transacoes`:
  - `POST`, `PUT` e `PATCH` passam a `403`;
  - `GET` passa a `GERENTE`;
  - a mensagem do `DELETE` é atualizada.
- `GET financeiro/resumo` e a função `Financeiro/resumo_operacoes` (equivalente ao `vw_resumo_operacoes`).
- `Financeiro/lancar_os_concluidas_legadas`, idempotente, executada uma vez pelo Run & Debug.

### Python

- `services/financeiro.py`: `PeriodoFinanceiro`, `TotalPorTipo`, `OperacaoFinanceira` e `ResumoFinanceiro`, com o fuso da loja (UTC−3 fixo).
- `XanoClient.resumo_financeiro`, somente leitura.
- `OrdemServicoDetalhe`: `id_transacao` e `data_lancamento`.

### Reflex

- **Oficina:**
  - indicador "Faturada · transação #N" no detalhe da OS;
  - aviso do valor a lançar no painel de conclusão.
- **Nova página `/financeiro` (GERENTE):**
  - período com atalhos;
  - cartões de receitas, despesas e saldo;
  - tabela por tipo;
  - lista de operações com filtro por tipo e busca locais.
- **Shell e tema:** rota em `ROUTE_ROLES`, seção "Gestão" na navegação, atalho no dashboard e cores `RECEITA`/`DESPESA` com contraste testado.

### Testes e documentação

- Contratos XanoScript, DTOs e cliente, estado da página, oficina, layout, tema e integração.
- `docs/domain-model.md`, `docs/xano-api-client.md`, `docs/project-structure.md`, a nova spec `financeiro.md` e o delta em `oficina-ordens-servico.md`.

## Impacto

| Área | Impacto |
| --- | --- |
| Oficina / OS | A conclusão passa a gravar uma transação; o contrato da rota não muda (a resposta continua sendo o detalhe). |
| Transações | Clientes externos que usavam o CRUD genérico passam a receber `403`. O Reflex não o usa. |
| Perfis | O `GERENTE` ganha `/financeiro` e deixa de lançar transações manualmente; `VENDEDOR` e `MECANICO` já não leem transações desde o saneamento pós-Change 9. |
| Entradas e vendas | Sem alteração; passam a aparecer no resumo. |
| Dados | Campo aditivo em `transacoes`; lançamentos retroativos das OS concluídas (D10). Transações antigas do CRUD genérico entram no resumo como estão. |
| Deploy | Push aditivo, sem `--sync`; execução única da função de D10. |

## Matriz de acesso

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Concluir OS (gera lançamento) | sim | não | sim |
| Consultar transações | sim | não | não |
| Criar, editar ou excluir transação manualmente | não | não | não |
| Visão consolidada (`/financeiro`) | sim | não | não |

## Fora do escopo

- Venda no balcão (`BALCAO`/`PECAS`), itens de transação e baixa de estoque por venda (Change 11).
- Estorno de transações, vendas e entradas.
- Forma de pagamento, parcelas, contas a receber e a pagar, nota fiscal.
- Comissões, custo médio e margem.
- Exportação (CSV ou PDF) e gráficos.
- Tela de administração de usuários (`/admin`).

## Critérios de aceite

- **Conclusão com itens:** concluir uma OS com total R$ X cria exatamente uma transação `ORDEM_SERVICO` de R$ X, com `id_os`, cliente, moto, data da conclusão e o funcionário do JWT. O detalhe da OS mostra a transação.
- **Conclusão sem valor:** concluir uma OS com total zero não cria transação, e o detalhe informa que não houve lançamento.
- **Atomicidade:** se o lançamento falhar, a OS continua `EM_ANDAMENTO` e nada é gravado.
- **Concorrência:** duas conclusões simultâneas da mesma OS resultam em uma única transição e uma única transação.
- **Cancelamento:** cancelar uma OS não cria transação.
- **Imutabilidade:** `POST transacoes`, `PUT`/`PATCH`/`DELETE transacoes/{id}` respondem `403` para qualquer perfil.
- **Acesso:** `VENDEDOR` e `MECANICO` recebem `403` em `GET transacoes` e em `GET financeiro/resumo`, e não veem `/financeiro` na navegação.
- **Resumo:**
  - receitas, despesas, saldo e totais por tipo batem com a soma das transações e entradas do período;
  - um período com fim antes do início ou com mais de 366 dias responde `400`;
  - acima de 500 operações, a resposta indica `truncado` e os totais continuam cobrindo o período inteiro.
- **Retroativo:** a função de D10 lança cada OS concluída com total positivo e sem transação; executá-la de novo não duplica nada.
- **UI:** a página `/financeiro` filtra por tipo e busca sem nova chamada ao Xano e mostra o aviso de truncamento quando houver.
- **Verificação antes do Archive:** suíte automatizada, `py_compile`, `reflex compile --dry`, validador XanoScript e `--dry-run` do push executados.

## Dependências

- Changes 7 e 9 publicadas no Xano (`Oficina/totais_os`, `historico_status_os`, transações `MOTO`).
- Credenciais `XANO_TEST_*` com `XANO_TEST_ALLOW_WRITES=true` para a integração com escrita, de preferência num branch do Xano.
- O resultado da integração da Change 9 sobre valores nulos em índice único, que sustenta a decisão D8.

## Decisões para validação

Detalhadas em `design.md` §3:

- **D1:** escopo financeiro; o balcão fica para a Change 11.
- **D2:** lançamento na conclusão; total zero conclui sem lançamento.
- **D3:** autoria de quem conclui.
- **D4:** entradas não geram `COMPRA`; o resumo lê as entradas diretamente.
- **D5:** CRUD manual em `403`.
- **D6:** leitura financeira só para o `GERENTE`.
- **D7:** período de até 366 dias e lista de até 500 operações.
- **D8:** `btree` simples em `id_os`.
- **D9:** fuso UTC−3 fixo.
- **D10:** lançamento retroativo das OS concluídas.

## Status

Apply concluído e verificado em 2026-10-09 (decisões D1 a D10 aprovadas).

- `python -m pytest`: 332 aprovados, 33 de integração ignorados (opt-in); `unittest` compatível.
- `py_compile` (63 módulos), `reflex compile --dry` e validador XanoScript (126 arquivos) sem erros.
- `xano workspace push -d ./xano --dry-run`: só criações e atualizações, sem exclusões e sem `--sync`.
- Verificação visual de `/financeiro` e do detalhe de OS faturada em 1440 px e 500 px (Playwright).

Pendente fora do repositório: push, execução única de `Financeiro/lancar_os_concluidas_legadas` e integração com credenciais. O arquivamento vem depois.
