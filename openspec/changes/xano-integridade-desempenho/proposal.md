# Proposta: integridade e desempenho do backend Xano (Change 16)

## Contexto e objetivo

Revisão das tabelas e dos endpoints pedida em 2026-10-22, depois do incidente do registro inserido pelo painel do Xano. A Change 15 deixou o frontend tolerante a esses registros; esta change trata o backend. Estado verificado na revisão:

- Os 129 `.xs` de `xano/` passam no validador do MCP `xano-developer`.
- O Xano publicado bate com `xano/`, fora a formatação que o servidor reescreve, com duas exceções:
  - `modelos_moto` tem `galeria` (`image[1:10]?`) e `default_motos` (`text?`), criadas pelo painel e nunca versionadas;
  - o agente e a tool de exemplo do Xano (`xano:quick-start`) existem só no publicado.
- Os endpoints genéricos de escrita (PUT e DELETE de motos, transações, itens e afins) já estão bloqueados com `precondition (false)`. Todos os endpoints do grupo HARLEY, exceto a vitrine pública, passam por `enforce_role`.

O objetivo é alinhar o versionado com o publicado, corrigir a ordem de baixa de estoque da entrada, reduzir o custo de `GET motos` e garantir no banco o que hoje só o endpoint confere.

## Escopo proposto

**Sem mudança de banco** (o push exige `--dry-run` revisado e o OK do usuário):

1. **`GET motos`:** hoje lê as tabelas inteiras de `modelos_moto`, `clientes` e `funcionarios` a cada chamada e faz um `find` por unidade, então o custo cresce com unidades × (clientes + funcionários + modelos). Passa a usar `join` à esquerda com `eval`, no padrão de `GET ordens_servico`, devolvendo os mesmos campos.
2. **`POST entrada_mercadoria`:** `|sort:"id_produto":"int":false` usa um tipo que o filtro não documenta (`number`, `text`, `natural`, `itext`, `inatural`). Além disso, ordena ao contrário da venda de balcão e do cancelamento de OS, que movimentam o estoque em ordem crescente de `id` pelo banco. Duas transações com os mesmos produtos em ordens opostas podem se bloquear no índice único do livro (`id_produto`, `versao_anterior`), e o banco aborta uma delas. A entrada passa a usar a mesma ordem, também pelo banco.
3. **`GET ordens_servico`:** a consulta de funcionários traz todas as colunas para mapear dois nomes. Passa a usar `output = ["id", "nome_funcionario"]`.
4. **Verificar, sem alterar, `Financeiro/resumo_operacoes`:** o exemplo da documentação do `sort` é ambíguo quanto ao terceiro argumento. Se `false` ordenar de forma crescente, o limite de 500 guarda as operações mais antigas. A conferência é feita com uma sessão de gerente, olhando a ordem do resumo.

**No cliente Reflex** (sem push):

- **Sanitização e observabilidade das respostas 5xx** (feito em 2026-10-25): o log `ERROR` passa a trazer a `message` do Xano, que nomeia o passo que falhou, em uma linha e com mascaramento de dados pessoais e numéricos: e-mails, códigos de 5 ou mais caracteres com letras e dígitos (placa, chassi) e sequências de 3 ou mais dígitos (CPF, telefone, ids) viram `…`. O texto é cortado em 200 caracteres, e corpo que não é JSON não é registrado. As mensagens `400` continuam como o Xano as envia, porque vão para a tela.

**Correções da auditoria E2E de 2026-10-27** (sem mudança de banco; push com o OK do usuário):

- `Quick Start/enforce_role` recusa o perfil com `precondition` `accessdenied`: o `throw` anterior chegava ao app como HTTP 200 com o erro no corpo, e não houve vazamento nem gravação.
- `Vendas/detalhe_moto` lê modelo, cliente e vendedor por joins à esquerda: com `db.get` e valor nulo, o detalhe de toda unidade sem reserva respondia 400.

**Com mudança de banco** (cada item precisa de OK antes de editar e de novo antes do push):

5. **`modelos_moto`:** versionar `galeria` e `default_motos` em `xano/table/modelos_moto.xs`, ou removê-las com `--sync`. **Atualização (2026-10-27):** a Change 17 versionou as duas como publicadas e levou a `galeria` à vitrine e a `/vendas`; resta decidir `default_motos`. Recomendação:
   - versionar `galeria` e levá-la à vitrine numa change própria (o DTO `ModeloCatalogo.galeria` já existe desde a Change 13);
   - remover `default_motos`, que repete a convenção de arquivo local `default_<slug>.png`.
6. **`entrada_mercadoria`:** índice único em (`id_fornecedor`, `numero_documento`). Hoje a duplicidade é conferida antes do insert, sem garantia no banco: dois envios simultâneos do mesmo documento lançariam a entrada, e o estoque, duas vezes. Antes de criar o índice, é preciso conferir se já há duplicatas publicadas.
7. **`event_log`:** índice em `user_id`, filtro de `GET logs/user/my_events`.
8. **`motos.id_modelo`:** é anulável por causa das unidades anteriores à Change 8, que usam `marca` e `modelo` legados. Uma unidade criada pelo painel sem modelo nunca aparece na vitrine e aparece em `/vendas` sem nome nem cores. As opções são:
   - tornar o campo obrigatório depois de atribuir um modelo às unidades legadas (`--sync`);
   - manter como está e documentar que motos se cadastram pelo app.

   Recomendação: manter por ora e documentar.

## Fora do escopo

- Remover o agente e a tool de exemplo do Xano. São inofensivos, e só um `--sync --delete` os apagaria.
- Otimizar o laço modelos × unidades de `Catalogo/vitrine`: o custo é baixo no volume atual, e o catálogo fica 60 s em cache no Reflex.
- Foto de um modelo sem nenhuma foto: hoje a tela aponta para `default_<slug>.png` mesmo sem o arquivo, o que dá 404 (comportamento da Change 13, coberto por teste). Trocar por uma imagem neutra é decisão de interface.
- Paginação das listas de cadastros.

## Riscos

- O plano Free publica direto em produção. Antes de qualquer push, resolver o token do Swagger (`docs/xano-api-client.md`) e revisar o `--dry-run`.
- O índice único de `entrada_mercadoria` falha se já houver duplicatas.
- `galeria` guarda arquivos enviados ao Xano. Um `--sync` sem a coluna versionada apagaria a coluna e as fotos.

## Status

Proposta em 2026-10-22, aguardando a aprovação do escopo e das decisões de banco (itens 5 a 8).
