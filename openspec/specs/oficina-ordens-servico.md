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

## Requisito: imutabilidade e itens

`PUT`, `PATCH` e `DELETE ordens_servico/{id}` DEVEM responder `403`. As mutações de `itens_ordem_servico` DEVEM responder `403` até a Change de itens com baixa de estoque; a leitura permanece liberada.

## Requisito: matriz de acesso

| Operação | GERENTE | MECANICO | VENDEDOR |
| --- | --- | --- | --- |
| Consultar OS, detalhe e histórico por moto | sim | sim | sim |
| Abrir OS e transicionar status | sim | sim | não |
| Listar mecânicos (`GET oficina/mecanicos`, apenas id e nome) | sim | sim | não |

### Cenário: vendedor

- **DADO** um vendedor autenticado
- **QUANDO** acessar `/workshop`
- **ENTÃO** DEVE ver a lista e o detalhe, sem "Nova OS" e sem ações de transição
- **E** chamadas forjadas de abertura ou transição DEVEM receber `403`
