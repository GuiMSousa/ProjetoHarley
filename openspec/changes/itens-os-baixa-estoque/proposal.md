# Proposta: itens da OS com baixa atômica de estoque e integridade financeira

## Contexto

A Change 6 entregou a abertura de OS, a máquina de estados com histórico e a página `/workshop`. Ela está publicada no Xano: os guids de `historico_status_os`, `Oficina/detalhe_os`, `Oficina/validar_transicao_os`, `POST ordens_servico/{id}/status` e `GET oficina/mecanicos` já foram gravados de volta no repositório. As OS, porém, ainda não têm conteúdo: não registram peças nem mão de obra.

Estado atual do backend:

- `itens_ordem_servico` tem apenas `id_os`, `id_produto` (obrigatório), `quantidade` e `valor_total_item`. Não há tipo de item, valor unitário, descrição, autoria nem indicação de baixa de estoque.
- Todas as mutações de itens (`POST itens_ordem_servico`, `PUT`/`PATCH`/`DELETE itens_ordem_servico/{id}`) respondem `403` desde a Change 6 (D6). A leitura (`GET`) continua liberada.
- `ordens_servico` não guarda valores: não há total de peças, total de mão de obra nem total geral.
- O saldo de `produtos.estoque_qtd` só muda em `POST entrada_mercadoria`, que lê e grava o saldo dentro de uma transação. A Change 5 aceitou o risco de duas entradas simultâneas do mesmo produto se sobrescreverem. Não existe livro de movimentações: não dá para saber por que um saldo mudou.
- `POST ordens_servico/{id}/status` cancela a OS sem nenhum efeito sobre itens ou estoque.
- No Reflex, o detalhe da OS lista os itens em modo de leitura, com a nota "A inclusão de peças chega na próxima etapa".

## Problema

Sem itens, a OS não registra o que foi feito nem quanto custa. Liberar os itens exige três garantias que o backend ainda não oferece:

1. **Estoque:** uma peça incluída na OS precisa sair do estoque sem permitir saldo negativo, mesmo com duas OS (ou uma OS e uma entrada) disputando o mesmo produto ao mesmo tempo.
2. **Reversibilidade:** remover um item ou cancelar a OS precisa devolver ao estoque exatamente o que foi baixado, e nada além disso.
3. **Integridade financeira:** preços e totais precisam ser definidos pelo servidor, sem aceitar valores calculados no cliente, e nenhuma OS encerrada pode mudar.

## Objetivo

Permitir que `GERENTE` e `MECANICO` incluam e removam peças e serviços em OS `ABERTA` ou `EM_ANDAMENTO`, com:

- baixa de estoque atômica na inclusão da peça e devolução na remoção ou no cancelamento;
- registro de cada movimentação em um livro de estoque auditável;
- totais de peças, mão de obra e total geral recalculados pelo Xano a cada mudança;
- edição de itens no detalhe da OS em `/workshop`, com busca de produtos, saldo, preço e resumo de custos.

## Decisões de negócio

- **Momento da baixa (D1):** a peça sai do estoque **na inclusão** do item, e não na conclusão da OS. A peça fica reservada para a moto desde a separação, e a oficina não descobre na conclusão que a peça acabou.
- **Mão de obra como item (D2):** um item é `PECA` (produto do estoque) ou `SERVICO` (descrição livre com valor). Os serviços não movimentam estoque.
- **Preço (D3):** o valor unitário da peça é o `preco_venda` do produto no momento da inclusão, gravado como fotografia. O valor do serviço é informado por quem inclui. `valor_total_item` é sempre `quantidade × valor_unitario`, calculado no Xano.
- **Status editáveis:** os itens só mudam em OS `ABERTA` ou `EM_ANDAMENTO`. Em `CONCLUIDA` ou `CANCELADA`, inclusão e remoção são rejeitadas.
- **Conclusão:** concluir a OS não movimenta o estoque, porque as peças já saíram na inclusão.
- **Cancelamento (D5):** cancelar a OS devolve ao estoque todas as peças baixadas na mesma transação da mudança de status. Os itens e os totais continuam na OS como registro do que foi orçado.
- **Remoção (D5):** remover um item o apaga da OS; se for peça baixada, a quantidade volta ao estoque. O livro de movimentações guarda a saída e a devolução.
- **Produto repetido (D4):** a mesma peça não pode aparecer duas vezes na OS. Para mudar a quantidade, remove-se o item e inclui-se de novo.
- **Itens legados (D10):** os itens gravados antes desta Change não tiveram baixa. São tratados como peça sem baixa: podem ser removidos, mas não devolvem nada ao estoque.
- **Transação financeira:** o lançamento em `transacoes` (`ORDEM_SERVICO`) na conclusão continua fora desta Change e fica para a Change de fechamento financeiro.

## Escopo

### Xano

- **`itens_ordem_servico`:** incluir `tipo_item` (`PECA`/`SERVICO`), `descricao`, `valor_unitario`, `estoque_baixado`, `id_funcionario` e `created_at`, e tornar `id_produto` anulável para os serviços. Este é o único relaxamento de restrição e exige `push --sync`.
- **`ordens_servico`:** incluir `valor_pecas`, `valor_servicos`, `valor_total` e `atualizado_em`, todos anuláveis.
- **`produtos`:** incluir `versao_estoque`. O `PATCH produtos/{id}` passa a descartar esse campo, como já faz com `estoque_qtd`.
- **Tabela nova `movimentacoes_estoque`:** livro de movimentações com índice único `(id_produto, versao_anterior)` (D6).
- **Funções novas:**
  - `Estoque/movimentar_estoque`: único ponto que altera `estoque_qtd`;
  - `Oficina/totais_os`: soma os itens por tipo.
- **Endpoints novos:**
  - `POST ordens_servico/{id}/itens`
  - `DELETE ordens_servico/{id}/itens/{item_id}`
- **Endpoints alterados:**
  - `POST ordens_servico/{id}/status` passa a devolver as peças ao cancelar;
  - `POST entrada_mercadoria` passa a movimentar o estoque por `Estoque/movimentar_estoque`, com a mesma resposta de antes;
  - `Oficina/detalhe_os` passa a devolver os totais e os campos novos dos itens.
- **Endpoints legados de itens:** `POST itens_ordem_servico` e `PUT`/`PATCH`/`DELETE itens_ordem_servico/{id}` continuam em `403`, com a mensagem apontando para as rotas novas.

### Python

- Em `services/ordens_servico.py`:
  - novo `TipoItemOS`;
  - DTO de inclusão `ItemOSCreate`, com as regras por tipo;
  - `ItemOrdemServico` evoluído, com os campos legados opcionais;
  - totais em `OrdemServicoResumo` e `OrdemServicoDetalhe`.
- No `XanoClient`: `adicionar_item_ordem_servico` e `remover_item_ordem_servico`, os dois devolvendo o detalhe. O seletor reutiliza o `list_produtos` que já existe.

### Reflex

- **Itens no detalhe da OS:** tipo, código ou descrição, quantidade, valor unitário e total, e uma ação de remover com confirmação.
- **Resumo de custos:** Total peças + Total mão de obra = Total OS, com os valores devolvidos pelo servidor e uma prévia do item em edição.
- **Painel "Adicionar item":**
  - alternância Peça | Serviço;
  - busca rápida de produtos ativos mostrando código, nome, saldo e preço;
  - produtos sem saldo aparecem desabilitados;
  - a quantidade é validada contra o saldo antes do envio.
- **Restrições:** painel e botões ocultos para `VENDEDOR` e em OS `CONCLUIDA` ou `CANCELADA`.
- **Erros:** passam por `feedback.error_feedback` e `AuthState._xano_error_response`. Depois de uma rejeição por saldo, o catálogo é recarregado para mostrar o saldo real.
- **Lista de OS:** ganha a coluna "Total".

### Testes e documentação

- **Testes:**
  - unitários de DTOs, cliente HTTP, regras puras e eventos do estado;
  - contratos XanoScript;
  - atualização dos contratos da entrada de mercadoria;
  - cenários de integração opcionais para baixa, devolução, cancelamento e bloqueios.
- **Documentação, no Archive:** atualizar `docs/domain-model.md` e `docs/xano-api-client.md`, e as specs `openspec/specs/oficina-ordens-servico.md` e `openspec/specs/estoque-entradas.md` (livro de movimentações).

## Matriz de acesso

| Operação | GERENTE | MECANICO | VENDEDOR |
| --- | --- | --- | --- |
| Ver itens e totais da OS | sim | sim | sim |
| Incluir peça ou serviço em OS `ABERTA`/`EM_ANDAMENTO` | sim | sim | não |
| Remover item de OS `ABERTA`/`EM_ANDAMENTO` | sim | sim | não |
| Alterar itens de OS `CONCLUIDA`/`CANCELADA` | não | não | não |
| Rotas legadas de mutação de `itens_ordem_servico` | não | não | não |
| Consultar o catálogo de produtos (`GET produtos`) | sim | sim | sim (já existente) |

## Fora do escopo

- Lançamento financeiro da OS em `transacoes` (`ORDEM_SERVICO`) e forma de pagamento.
- Catálogo de serviços com preço tabelado, desconto, acréscimo e comissão.
- Edição da quantidade de um item existente: para mudar, remove-se e inclui-se de novo.
- Tela de consulta do livro de movimentações (kardex) e ajuste manual de estoque.
- Estorno de entrada de mercadoria.
- Paginação server-side do catálogo de produtos.

## Critérios de aceite

- **Inclusão de peça:** em OS `ABERTA` ou `EM_ANDAMENTO`, grava o item com `valor_unitario = preco_venda` atual e `valor_total_item = quantidade × valor_unitario`, e reduz `estoque_qtd` na mesma quantidade, com uma linha `SAIDA_OS` no livro. Qualquer preço ou total enviado no payload é ignorado.
- **Saldo insuficiente:** a inclusão com `quantidade > estoque_qtd` é rejeitada com `400` "Saldo insuficiente para <código>: disponível X, solicitado Y.", sem gravar item, movimentação nem alteração de saldo.
- **Inclusões rejeitadas com `400`:**
  - produto inativo ou inexistente;
  - produto que já está na OS;
  - quantidade `< 1`;
  - serviço sem descrição ou sem valor positivo;
  - OS `CONCLUIDA` ou `CANCELADA`.
- **Remoção:** remover uma peça baixada devolve a quantidade ao estoque com uma linha `ESTORNO_OS`. Remover um serviço ou um item legado não movimenta o estoque.
- **Cancelamento:** cancelar a OS devolve todas as peças baixadas na mesma transação da mudança de status. Se a devolução falhar, o status não muda.
- **Concluir:** concluir a OS não altera o estoque.
- **Totais:**
  - depois de cada inclusão ou remoção, `valor_pecas`, `valor_servicos` e `valor_total` da OS são iguais à soma dos itens por tipo;
  - o detalhe sempre mostra os totais calculados a partir dos itens.
- **Concorrência:**
  - duas inclusões simultâneas que juntas excedem o saldo nunca deixam o saldo negativo nem uma baixa sem registro: uma delas é rejeitada;
  - uma entrada de mercadoria simultânea a uma baixa do mesmo produto não perde nenhuma das duas;
  - uma inclusão simultânea ao cancelamento da mesma OS termina em um de dois estados: o item é incluído e devolvido pelo cancelamento, ou a inclusão é rejeitada.
- **Estoque e auditoria:**
  - para todo produto movimentado a partir desta Change, `estoque_qtd` é igual ao saldo posterior da sua última movimentação no livro;
  - `POST entrada_mercadoria` mantém o contrato e passa a gerar linhas `ENTRADA`.
- **Perfis e rotas:**
  - o `VENDEDOR` vê itens e totais, sem painel nem botões;
  - chamadas forjadas de inclusão ou remoção recebem `403`;
  - as rotas legadas de mutação de itens continuam em `403`.
- **UI:**
  - em `/workshop`, a OS encerrada não exibe o painel de itens nem os botões de remover;
  - a tentativa sem saldo exibe o erro e recarrega o saldo.
- **Verificação antes do Archive:** suíte automatizada, `py_compile`, `reflex compile --dry` e validação XanoScript executados.

## Dependências

- A Change 6 publicada no Xano, o que já está confirmado pelos guids no repositório.
- Produtos ativos com saldo e ao menos uma OS `ABERTA` para os testes de integração, com `XANO_TEST_ALLOW_WRITES=true`, de preferência em um branch do Xano.
- `push --sync` para o relaxamento de `itens_ordem_servico.id_produto`, com o repositório em sincronia com o workspace.

## Decisões para validação

- **D1 — Baixa na inclusão:** a peça sai do estoque ao ser incluída na OS e volta na remoção ou no cancelamento; concluir não movimenta nada. A alternativa, baixar na conclusão, deixa o saldo aparente maior que o físico durante o serviço e pode impedir a conclusão por falta de peça. *Recomendado.*
- **D2 — Serviço como item da mesma tabela:** `tipo_item = SERVICO` em `itens_ordem_servico`, com `descricao` e `valor_unitario` informados e sem produto. Mantém uma rota, uma lista e uma soma. Custa o relaxamento de `id_produto` via `push --sync`. A alternativa é uma tabela `servicos_ordem_servico` separada, sem `--sync` e com duas rotas. *Recomendado.*
- **D3 — Preço da peça no servidor e serviço informado:** a peça usa `preco_venda` gravado como fotografia. O serviço tem o valor digitado por `GERENTE` ou `MECANICO`, porque ainda não existe catálogo de serviços. *Confirmar quem pode informar o valor do serviço.*
- **D4 — Produto repetido rejeitado:** a mesma peça aparece uma única vez na OS; para ajustar a quantidade, remove-se e inclui-se de novo. *Recomendado.*
- **D5 — Remoção física e cancelamento conservador:** o item removido é apagado, e o livro de movimentações preserva a saída e a devolução. No cancelamento, os itens e os totais permanecem na OS, e só as peças voltam ao estoque. *Recomendado.*
- **D6 — Livro de movimentações com versão por produto:** a tabela `movimentacoes_estoque` registra cada movimentação com saldo anterior e posterior. O índice único `(id_produto, versao_anterior)`, somado ao campo `produtos.versao_estoque`, faz a segunda movimentação concorrente do mesmo produto falhar no banco e desfazer a transação. É o mesmo padrão validado na Change 6 com o histórico de status. `POST entrada_mercadoria` passa a usar a mesma função, o que fecha o risco de sobrescrita aceito na Change 5. Isto amplia o escopo para a entrada de mercadoria, sem mudar o contrato dela. *Recomendado.*
- **D7 — Serialização das mutações da mesma OS:** toda inclusão, remoção e transição começa atualizando `ordens_servico.atualizado_em`, o que trava a linha da OS, e só então relê o status. Isso impede incluir um item numa OS que está sendo cancelada sem que a peça volte ao estoque. *Recomendado; será validado no Apply (ver riscos).*
- **D8 — Totais gravados e recalculados:** a cada mutação, o Xano grava na OS os totais somados a partir dos itens, que a lista usa. O detalhe recalcula a partir dos itens, que são a fonte de verdade, e assim também cobre OS legadas sem totais. *Recomendado.*
- **D9 — Rotas aninhadas:** `POST ordens_servico/{id}/itens` e `DELETE ordens_servico/{id}/itens/{item_id}`, ambas devolvendo o detalhe atualizado da OS. As rotas legadas de mutação continuam em `403`, e `GET itens_ordem_servico` é mantido. *Recomendado.*
- **D10 — Itens legados:** `tipo_item` nulo é tratado como `PECA` e `estoque_baixado` nulo como "sem baixa". Esses itens podem ser removidos e não devolvem estoque. *Recomendado.*
- **D11 — Quem edita itens:** qualquer `GERENTE` ou `MECANICO` edita os itens de qualquer OS editável, coerente com a D7 da Change 6. *Confirmar.*
