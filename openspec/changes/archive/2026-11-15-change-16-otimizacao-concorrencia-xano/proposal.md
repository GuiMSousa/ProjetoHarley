# Proposta: otimização, JOINs e concorrência no backend Xano (Change 16)

## Contexto e objetivo

Revisão das tabelas e dos endpoints pedida em 2026-10-22, depois do incidente do registro inserido pelo painel do Xano. A Change 15 deixou o frontend tolerante a esses registros; esta change trata o backend. Estado verificado na revisão:

- Os 129 `.xs` de `xano/` passam no validador do MCP `xano-developer`.
- O Xano publicado bate com `xano/`, fora a formatação que o servidor reescreve, com duas exceções:
  - `modelos_moto` tem `galeria` (`image[1:10]?`) e `default_motos` (`text?`), criadas pelo painel e nunca versionadas (a Change 17 versionou as duas);
  - o agente e a tool de exemplo do Xano (`xano:quick-start`) existem só no publicado.
- Os endpoints genéricos de escrita (PUT e DELETE de motos, transações, itens e afins) já estão bloqueados com `precondition (false)`. Todos os endpoints do grupo HARLEY, exceto a vitrine pública, passam por `enforce_role`.

O objetivo é alinhar o versionado com o publicado, tirar as leituras por registro (N+1) dos fluxos de Balcão, Oficina e Entradas, conferir que nenhuma alteração de status ou de estoque escapa das travas de versão, garantir que toda recusa responda com o status HTTP certo e limpar o schema.

**Ampliação de 2026-11-11:** o escopo passou a incluir os JOINs de Balcão, Oficina e Entradas, a trava de concorrência em Vendas e Estoque, a auditoria de 403 em todos os `.xs` e a limpeza de schema. A pasta foi renomeada de `xano-integridade-desempenho` para `change-16-otimizacao-concorrencia-xano`; os itens 1 a 8 mantêm a numeração, porque `xano/table/modelos_moto.xs` cita o item 5.

## Mapeamento de 2026-11-11

Leitura de `xano/function/` e `xano/api/`, sem chamar o Xano. A baseline local estava limpa: `ruff` sem violações, `compileall` OK e `pytest` com 441 aprovados e 43 ignorados.

### Leituras por registro ou sem join

| Prioridade | Onde | Hoje | Proposta |
| --- | --- | --- | --- |
| 1 | `Oficina/detalhe_os`, resposta de `GET ordens_servico/{id}` e das 4 escritas da OS | 5 `db.get` (moto, cliente, autor, mecânico) | Item 9 |
| 2 | `GET ordens_servico` | Lê `funcionarios` inteira, com todas as colunas, e faz dois `find` por OS: custo OS × funcionários | Item 10 (substitui o item 3) |
| 3 | `GET entrada_mercadoria` | Uma consulta `count` de `itens_compra_estoque` por entrada | Item 11 |
| 4 | Pré-checagens de `POST balcao/vendas` (até 30 itens) e `POST entrada_mercadoria` (sem teto) | Um `db.get produtos` por item | Item 12 |

Já usam join e ficam como estão: `Balcao/detalhe_venda`, `Estoque/detalhe_entrada`, `Vendas/detalhe_moto`, `GET motos` e `Financeiro/resumo_operacoes` (os laços deste último são só em memória). As funções de uso único (`lancar_os_concluidas_legadas`, `normalizar_entradas_legadas` e `seed_exemplo`) ficam fora.

### Concorrência de status e estoque

Nenhuma alteração de status ou de saldo escapa das travas de versão:

- **Estoque:** só `Estoque/movimentar_estoque` altera `estoque_qtd`, com o índice único (`id_produto`, `versao_anterior`) do livro. Quem chama:
  - a venda de balcão;
  - a entrada de mercadoria;
  - a inclusão e a remoção de itens da OS;
  - o cancelamento de OS.

  `PATCH produtos` descarta `estoque_qtd` e `versao_estoque` do payload, e `PUT produtos` não grava saldo.
- **Moto:** só `Vendas/transicionar_moto` altera `motos.status`, com o índice único (`id_moto`, `versao_anterior`). É usada pela reserva, pelo cancelamento e pela venda. `PUT motos` está bloqueado, e `PATCH motos` não aceita status.
- **OS:** índice único (`id_os`, `status_anterior`) no histórico. A inclusão de itens e a transição de status travam a linha da OS (`atualizado_em`) antes de reler o status.
- **Repetição:** a `chave_venda` é única por produto no balcão, e o documento é único por fornecedor na entrada (índice criado na Change 5, em 2026-09-24).

Lacunas menores, nos itens 13 e 14:

- `PATCH motos/{id}` muda preço e cor de uma moto `RESERVADA`, sem conferir versão. O chassi só muda com a moto disponível, mas essa conferência roda fora de transação.
- `POST produtos` grava o saldo inicial sem lançamento no livro, então a soma do livro não reconcilia com `estoque_qtd`.

### Recusas e status HTTP

- Não há mais nenhum `throw` nos 129 `.xs`. O contrato estático cobre só `enforce_role`.
- Toda `precondition` tem `error_type`, menos uma em `Quick Start/generate_magic_link`. A função veio do modelo do Xano e nenhum endpoint a chama.
- As recusas de acesso usam `accessdenied`: `enforce_role`, usuário sem funcionário vinculado e endpoints bloqueados. `seed_gerente` e `lancar_os_concluidas_legadas` usam `inputerror` para "não é gerente", mas são funções de console e não recusas de uma requisição.
- Ao vivo, só `GET fornecedores` como VENDEDOR foi confirmado com 403 depois do push de 2026-10-27. Os 5 testes de controle de acesso da integração ainda não foram repetidos. **Atualização (2026-11-15):** as recusas do VENDEDOR e do MECANICO nesses testes deram 403 ao vivo, e o GERENTE leu fornecedores, funcionários e o resumo financeiro (ver `tasks.md`). A recusa do MECANICO no balcão continua sem prova, porque produção não tem produto ativo.

## Escopo proposto

**Sem mudança de banco** (o push exige `--dry-run` revisado e o OK do usuário):

1. **`GET motos`:** usa `join` à esquerda com `eval`, no lugar das tabelas inteiras e do `find` por unidade. Feito e publicado.
2. **`POST entrada_mercadoria`:** `|sort:"id_produto":"int":false` usa um tipo que o filtro não documenta (`number`, `text`, `natural`, `itext`, `inatural`). Além disso, ordena ao contrário da venda de balcão e do cancelamento de OS, que movimentam o estoque em ordem crescente de `id` pelo banco. Duas transações com os mesmos produtos em ordens opostas podem se bloquear no índice único do livro, e o banco aborta uma delas. A entrada passa a usar a mesma ordem, também pelo banco.
3. **`GET ordens_servico`:** restringir a consulta de funcionários com `output = ["id", "nome_funcionario"]`. Fica como alternativa caso o item 10 não seja viável. **Descartado (2026-11-14):** o item 10 foi publicado e a consulta inteira de funcionários deixou de existir.
4. **Verificar, sem alterar, `Financeiro/resumo_operacoes`:** o exemplo da documentação do `sort` é ambíguo quanto ao terceiro argumento. Se `false` ordenar de forma crescente, o limite de 500 guarda as operações mais antigas. A conferência é feita com uma sessão de gerente. **Atualização (2026-11-15):** com o GERENTE, o resumo responde e o DTO valida. A ordem segue sem verificação: há 0 operações nos últimos 360 dias, e a doc ainda chama o argumento de `asc` enquanto o exemplo com `true` devolve a lista decrescente.

Ampliação de 2026-11-11:

9. **`Oficina/detalhe_os`:** uma `db.query` com joins à esquerda em `motos_clientes`, `clientes` e duas vezes em `funcionarios` (apelidos `autor` e `mecanico`), com `return = {type: "single"}`, devolvendo os mesmos campos. Hoje um `db.get` com valor nulo responde 400 "Missing param: field_value", como no A2. O app sempre grava moto e mecânico, então o risco está em OS criadas pelo painel ou legadas. Nesse caso, a escrita de item ou de status é gravada e a resposta chega como 400, e o usuário vê erro numa operação que já aconteceu. O `id_cliente` mantém o fallback do dono da moto.
10. **`GET ordens_servico`:** autor e mecânico por joins com apelido, sem ler a tabela inteira e sem o laço. Antes, é preciso confirmar no validador e numa leitura ao vivo que o Xano aceita a mesma tabela em dois apelidos; se não aceitar, aplica-se o item 3.
11. **`GET entrada_mercadoria`:** `quantidade_itens` por um addon de contagem (padrão documentado do XanoScript) ou por uma única consulta dos itens das entradas listadas, contada em memória. O campo e o formato da resposta não mudam.
12. **Pré-checagens de produto:** uma `db.query` com `id in $ids_produto` em `POST balcao/vendas` e `POST entrada_mercadoria`, mantendo a mensagem por produto. A entrada não tem teto de itens, ao contrário do balcão (30); o teto é uma decisão (item 16).
13. **`PATCH motos/{id}`:** **decidido e publicado (2026-11-14):** preço e cor de uma moto `RESERVADA` ou `VENDIDA` não mudam, e reenviar o valor atual é aceito. O status é conferido antes da transação e de novo dentro dela, depois da gravação que trava a linha; isso substituiu a conferência de `versao_status` que este item sugeria. A recusa é `inputerror` (400), porque o Xano não tem `error_type` para 422.
14. **`POST produtos`:** **decidido e publicado (2026-11-14):** o produto nasce com saldo 0, e o estoque entra pela entrada de mercadoria, que grava o livro. Um saldo diferente de 0 recebe 400, e o formulário e o `ProdutoCreate` não têm mais o saldo inicial. A alternativa de lançar o saldo inicial como `ENTRADA` foi descartada.
15. **Recusas:** contrato estático que proíbe `throw` em todos os `.xs` e exige `error_type` em toda `precondition`. `generate_magic_link` recebe `inputerror`.

**No cliente Reflex** (sem push):

- **Sanitização e observabilidade das respostas 5xx** (feito em 2026-10-25): o log `ERROR` passa a trazer a `message` do Xano, que nomeia o passo que falhou, em uma linha e com mascaramento de dados pessoais e numéricos: e-mails, códigos de 5 ou mais caracteres com letras e dígitos (placa, chassi) e sequências de 3 ou mais dígitos (CPF, telefone, ids) viram `…`. O texto é cortado em 200 caracteres, e corpo que não é JSON não é registrado. As mensagens `400` continuam como o Xano as envia, porque vão para a tela.

**Correções da auditoria E2E de 2026-10-27** (feitas e publicadas; o `--dry-run` seguinte não mostrou diferenças):

- `Quick Start/enforce_role` recusa o perfil com `precondition` `accessdenied`: o `throw` anterior chegava ao app como HTTP 200 com o erro no corpo, e não houve vazamento nem gravação.
- `Vendas/detalhe_moto` lê modelo, cliente e vendedor por joins à esquerda: com `db.get` e valor nulo, o detalhe de toda unidade sem reserva respondia 400.

**Com mudança de banco** (cada item precisa de OK antes de editar e de novo antes do push):

5. **`modelos_moto`:** a Change 17 versionou `galeria` e `default_motos` como publicadas e levou a `galeria` à vitrine e a `/vendas`. Resta decidir `default_motos`; a recomendação é removê-la, porque repete a convenção de arquivo local `default_<slug>.png`, que a Change 17 eliminou. **Não executado:** a remoção exige `--sync` e o OK do usuário. Transferido para os débitos conhecidos de `docs/quality.md` (2026-11-16).
6. **`entrada_mercadoria`:** ~~índice único em (`id_fornecedor`, `numero_documento`)~~. **Correção (2026-11-11):** o índice já existe desde a Change 5 e já protege os envios simultâneos do mesmo documento. Nada a fazer no banco; falta só o cenário concorrente do item 17.
7. **`event_log`:** índice em `user_id`, filtro de `GET logs/user/my_events`. **Não executado:** é mudança de banco e exige o OK do usuário. Transferido para os débitos conhecidos (2026-11-16).
8. **`motos.id_modelo`:** é anulável por causa das unidades anteriores à Change 8, que usam `marca` e `modelo` legados. Uma unidade criada pelo painel sem modelo nunca aparece na vitrine e aparece em `/vendas` sem nome nem cores. As opções são:
   - tornar o campo obrigatório depois de atribuir um modelo às unidades legadas (`--sync`);
   - manter como está e documentar que motos se cadastram pelo app.

   Recomendação: manter por ora e documentar. Em 2026-10-27 produção tinha uma unidade sem modelo. **Decidido (2026-11-15):** mantido como está, sem mudança de banco, e documentado em `docs/domain-model.md`.

**Decisões e testes:**

16. **Teto de itens da entrada de mercadoria:** sem teto, uma nota grande deixa a transação e as travas de estoque abertas por mais tempo. **Decidido e publicado (2026-11-14):** 50 itens. O Xano recusa com 400 antes da transação, o DTO do Reflex aplica o mesmo limite e o formulário recusa a 51ª linha no "Adicionar item".
17. **Cenários concorrentes novos:** a integração já tem 6:
    - duas OS disputando o saldo;
    - item incluído durante o cancelamento;
    - duas reservas da mesma moto;
    - duas vendas da mesma moto;
    - duas conclusões da mesma OS;
    - duas vendas de balcão do saldo inteiro.

    Faltam:
    - duas entradas com o mesmo documento;
    - duas entradas com os mesmos produtos em ordens opostas (item 2);
    - uma entrada e uma venda de balcão do mesmo produto.

## Fora do escopo

- Remover o agente e a tool de exemplo do Xano. São inofensivos, e só um `--sync --delete` os apagaria.
- O laço modelos × unidades de `Catalogo/vitrine`: o custo é baixo no volume atual, e o catálogo fica 60 s em cache no Reflex.
- Trava de versão nos cadastros (clientes, fornecedores, funcionários, motos de clientes): a última edição vence, sem efeito em estoque, status ou financeiro.
- Paginação das listas de cadastros.

## Riscos

- O plano Free publica direto em produção. Antes de qualquer push, resolver o token do Swagger (`docs/xano-api-client.md`) e revisar o `--dry-run`.
- Os cenários com escrita e concorrência gravam dados reais e exigem um workspace ou branch de testes. Sem ele, os itens 9 a 14 só têm cobertura estática e de leitura ao vivo.
- ~~Join da mesma tabela com dois apelidos (itens 9 e 10) ainda não foi usado neste workspace.~~ **Resolvido (2026-11-14):** os itens 9 e 10 foram publicados, o Xano guardou o código sem mudança (`--dry-run` seguinte sem diferenças), o detalhe de uma OS inexistente responde 404 sem 500 e a lista é lida. Resta ver os nomes de autor e mecânico preenchidos, o que exige uma OS no banco.
- Uma resposta lida por `detalhe_os` ou por `GET ordens_servico` precisa manter os mesmos campos, porque `services/` os valida com pydantic.
- `galeria` guarda arquivos enviados ao Xano. Um `--sync` sem a coluna versionada apagaria a coluna e as fotos.

## Status

Proposta em 2026-10-22 e ampliada em 2026-11-11. Em 2026-11-14 o usuário aprovou os itens 9 a 16 e decidiu:

- item 13: preço e cor bloqueados em moto reservada ou vendida;
- item 14: saldo inicial 0;
- item 16: teto de 50 itens.

Os itens 2 e 9 a 16 foram publicados em 2026-11-14, nas Entregas 1 e 2 (nos commits, "fase 1" e "fase 2"), e o item 3 foi descartado. Em 2026-11-15, as recusas do VENDEDOR e do MECANICO deram 403 ao vivo, e as leituras do GERENTE passaram. O item 8 foi decidido sem mudança de banco.

**Arquivada em 2026-11-15.** Foram para a seção "Débitos conhecidos" de `docs/quality.md`:

- os itens de banco 5 e 7, que não foram executados e exigem o OK do usuário;
- a ordem do resumo no item 4, que só pode ser conferida com 2 ou mais operações no período (a leitura como GERENTE passou em 2026-11-15);
- a recusa do MECANICO no balcão, que precisa de um produto ativo;
- os testes de escrita e concorrência do item 17, que dependem de um workspace de homologação.
