# Especificação: oficina e ordens de serviço

## Requisito: abertura de OS

`POST ordens_servico` DEVE criar a OS com `status = ABERTA`, `data_abertura` do servidor, `id_funcionario` do usuário autenticado e `id_cliente` igual ao dono da moto, ignorando esses campos no payload. A moto e o cliente DEVEM estar ativos; o mecânico responsável DEVE ser um funcionário ativo do tipo `MECANICO`; `tipo_servico` e `descricao_problema` são obrigatórios; `quilometragem`, quando informada, DEVE ser `>= 0`.

### Cenário: abertura por mecânico

- **DADO** um mecânico autenticado e uma moto ativa de cliente ativo sem OS em aberto
- **QUANDO** abrir uma OS corretiva sem informar o responsável
- **ENTÃO** a OS DEVE nascer `ABERTA`, com o mecânico como autor e responsável e o cliente da moto
- **E** o histórico DEVE ter uma linha `null → ABERTA`

### Cenário: gerente sem responsável

- **DADO** um gerente que não informa o mecânico
- **QUANDO** abrir a OS
- **ENTÃO** a resposta DEVE ser `400` "Informe o mecânico responsável."

### Cenário: payload adulterado

- **DADO** um payload com `status = CONCLUIDA`, `id_funcionario` e `id_cliente` de terceiros
- **QUANDO** a OS for aberta
- **ENTÃO** esses valores DEVEM ser ignorados

## Requisito: uma OS em aberto por moto

Uma moto com OS `ABERTA` ou `EM_ANDAMENTO` NÃO DEVE receber nova OS.

### Cenário: segunda abertura

- **DADO** uma moto com OS `EM_ANDAMENTO`
- **QUANDO** abrir outra OS para ela
- **ENTÃO** a resposta DEVE ser `400` e nenhuma OS DEVE ser criada

## Requisito: máquina de estados

O status DEVE mudar somente por `POST ordens_servico/{id}/status`, seguindo:

| De | Para |
| --- | --- |
| `ABERTA` | `EM_ANDAMENTO`, `CANCELADA` |
| `EM_ANDAMENTO` | `CONCLUIDA`, `CANCELADA` |
| `CONCLUIDA`, `CANCELADA` | nenhum (estados finais) |

`CANCELADA` DEVE exigir motivo. `data_inicio` DEVE ser preenchida ao iniciar e `data_encerramento` ao concluir ou cancelar.

### Cenário: transição inválida

- **DADO** uma OS `ABERTA`
- **QUANDO** tentar `CONCLUIDA` diretamente
- **ENTÃO** a resposta DEVE ser `400` e a OS NÃO DEVE mudar

### Cenário: reabertura

- **DADO** uma OS `CONCLUIDA` ou `CANCELADA`
- **QUANDO** tentar qualquer transição
- **ENTÃO** a resposta DEVE ser `400` "OS encerrada não pode ser reaberta ou alterada."

### Cenário: cancelamento sem motivo

- **DADO** uma OS `EM_ANDAMENTO`
- **QUANDO** cancelar sem motivo
- **ENTÃO** a resposta DEVE ser `400`

## Requisito: controle de concorrência

A transição DEVE informar `status_atual`; se a OS não estiver nesse status, a operação DEVE ser rejeitada sem efeito. O índice único `(id_os, status_anterior)` em `historico_status_os` DEVE impedir que duas transições simultâneas a partir do mesmo status sejam gravadas.

### Cenário: conflito

- **DADO** dois usuários vendo a mesma OS `ABERTA`
- **QUANDO** um a inicia e o outro tenta cancelá-la com `status_atual = ABERTA`
- **ENTÃO** a segunda operação DEVE ser rejeitada e a interface DEVE exibir o status real

## Requisito: histórico de status

Cada abertura e cada transição aceita DEVE gerar exatamente uma linha em `historico_status_os`, com o funcionário autenticado, a data e a observação.

## Requisito: histórico por moto

`GET ordens_servico?id_moto_cliente=` DEVE listar as OS da moto da mais recente para a mais antiga.

## Requisito: imutabilidade

`PUT`, `PATCH` e `DELETE ordens_servico/{id}` DEVEM responder `403`. As rotas genéricas de mutação de `itens_ordem_servico` (`POST`, `PUT`, `PATCH`, `DELETE`) DEVEM responder `403`; os itens mudam somente pelas rotas aninhadas da OS. A leitura permanece liberada.

## Requisito: itens da OS

`POST ordens_servico/{id}/itens` DEVE incluir uma peça (`PECA`, com produto) ou um serviço (`SERVICO`, com descrição e valor unitário) e `DELETE ordens_servico/{id}/itens/{item_id}` DEVE remover um item, ambos devolvendo o detalhe atualizado. Só OS `ABERTA` ou `EM_ANDAMENTO` DEVEM aceitar mutações de itens.

- A peça DEVE ter `valor_unitario = preco_venda` do produto no momento da inclusão e DEVE sair do estoque na mesma transação (`SAIDA_OS`).
- O serviço NÃO DEVE movimentar estoque.
- `valor_total_item` DEVE ser `quantidade × valor_unitario`, calculado pelo Xano; preços, totais, `estoque_baixado` e autoria enviados pelo cliente DEVEM ser ignorados.
- Um mesmo produto NÃO DEVE aparecer duas vezes na OS.
- Remover uma peça baixada DEVE devolvê-la ao estoque (`ESTORNO_OS`); serviços e itens legados NÃO DEVEM movimentar estoque.

### Cenário: inclusão de peça

- **DADO** uma OS `EM_ANDAMENTO` e o produto P1 ativo com estoque 5 e preço 45,90
- **QUANDO** um mecânico incluir P1 × 2
- **ENTÃO** o item DEVE ter valor unitário 45,90 e total 91,80
- **E** o estoque de P1 DEVE ficar em 3

### Cenário: saldo insuficiente

- **DADO** o produto P1 com estoque 1
- **QUANDO** incluir P1 × 2 numa OS aberta
- **ENTÃO** a resposta DEVE ser `400` com a mensagem de saldo insuficiente
- **E** a OS e o estoque NÃO DEVEM mudar

### Cenário: OS encerrada

- **DADO** uma OS `CONCLUIDA` ou `CANCELADA`
- **QUANDO** incluir ou remover um item
- **ENTÃO** a resposta DEVE ser `400` "OS encerrada não permite alterar itens."

## Requisito: estoque no ciclo da OS

Cancelar a OS DEVE devolver ao estoque todas as peças baixadas na mesma transação da transição; se alguma devolução falhar, o status NÃO DEVE mudar. Concluir ou iniciar a OS NÃO DEVE movimentar estoque. A OS cancelada DEVE manter itens e totais como registro.

### Cenário: cancelamento com peças

- **DADO** uma OS `EM_ANDAMENTO` com P1 × 2 baixado
- **QUANDO** for cancelada com motivo
- **ENTÃO** o estoque de P1 DEVE voltar ao valor anterior à inclusão
- **E** o item DEVE continuar listado na OS

## Requisito: totais da OS

A cada inclusão ou remoção, o Xano DEVE gravar na OS `valor_pecas`, `valor_servicos` e `valor_total = valor_pecas + valor_servicos`, somados a partir dos itens. O detalhe DEVE recalcular os totais a partir dos itens (itens legados sem tipo contam como peça).

## Requisito: serialização das mutações da OS

Inclusão, remoção e transição DEVEM começar atualizando `ordens_servico.atualizado_em`, travando a linha da OS, e só então reler status e itens. No cancelamento, os itens a devolver DEVEM ser consultados depois da atualização da OS.

### Cenário: inclusão durante o cancelamento

- **DADO** uma OS `ABERTA`
- **QUANDO** um usuário a cancelar enquanto outro inclui uma peça
- **ENTÃO** ou a inclusão é rejeitada, ou a peça incluída é devolvida pelo cancelamento
- **E** o estoque final DEVE ser igual ao anterior às duas operações

## Requisito: matriz de acesso

| Operação | GERENTE | MECANICO | VENDEDOR |
| --- | --- | --- | --- |
| Consultar OS, detalhe, itens, totais e histórico por moto | sim | sim | sim |
| Abrir OS e transicionar status | sim | sim | não |
| Incluir e remover peças e serviços | sim | sim | não |
| Listar mecânicos (`GET oficina/mecanicos`, apenas id e nome) | sim | sim | não |

### Cenário: vendedor

- **DADO** um vendedor autenticado
- **QUANDO** acessar `/workshop`
- **ENTÃO** DEVE ver a lista, o detalhe, os itens e os totais, sem "Nova OS", sem ações de transição e sem edição de itens
- **E** chamadas forjadas de abertura, transição, inclusão ou remoção de itens DEVEM receber `403`

## Requisito: itens na interface

Em `/workshop`, o detalhe de uma OS editável DEVE oferecer busca de peças com saldo e preço (produtos sem saldo desabilitados), inclusão de serviço, confirmação de remoção e o resumo "Peças + Mão de obra = Total OS", com prévia do item em edição. A quantidade DEVE ser validada contra o saldo antes do envio. Depois de uma rejeição do Xano, a interface DEVE recarregar detalhe e saldos.
