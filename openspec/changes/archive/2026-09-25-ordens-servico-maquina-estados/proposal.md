# Proposta: ordens de serviço — abertura, máquina de estados e oficina

## Contexto

As Changes 1 a 5 e o saneamento pré-Change 6 entregaram autenticação, cadastros, entradas de mercadoria com estoque atômico e o hardening do ambiente. A oficina ainda não tem fluxo próprio: `/workshop` é uma página vazia e os endpoints de `ordens_servico` são CRUD genérico.

Estado atual do backend:

- `ordens_servico` tem somente `id_moto_cliente`, `id_funcionario` (autoria), `data_abertura` e `status`. Não há descrição do problema, tipo de serviço, responsável técnico nem datas de início e encerramento.
- `POST ordens_servico` aceita `status` e `data_abertura` do payload, portanto uma OS pode nascer `CONCLUIDA`.
- `PUT` e `PATCH ordens_servico/{id}` permitem qualquer troca de status, inclusive reabrir OS encerrada. `DELETE` remove fisicamente.
- `POST`/`PUT`/`PATCH`/`DELETE itens_ordem_servico` gravam itens com valor informado pelo cliente e sem baixa de estoque.
- `GET ordens_servico` devolve registros crus, sem cliente, moto ou responsável.
- No Reflex, `/workshop` é restrito a `GERENTE` e `MECANICO`; o vendedor não consegue consultar a oficina.

## Problema

A oficina não consegue registrar, acompanhar e encerrar atendimentos com rastreabilidade. Sem uma máquina de estados no servidor, o status da OS pode ser alterado arbitrariamente, o que compromete o histórico por moto e as Changes seguintes (itens com baixa de estoque e fechamento financeiro), que dependem de um ciclo de vida confiável.

## Objetivo

Entregar a gestão de ordens de serviço sem movimentação de estoque:

- abertura de OS para uma moto de cliente ativa, com descrição do problema, tipo de serviço e mecânico responsável;
- transições de status exclusivamente por um endpoint dedicado, validadas no Xano e registradas em histórico;
- consulta da oficina em `/workshop` com filtros por status, busca, paginação, detalhamento e histórico de manutenção por moto.

## Decisões de negócio

- A OS sempre nasce `ABERTA`; `status`, `data_abertura`, autoria e cliente nunca são aceitos do payload.
- **Autoria e responsável são papéis distintos.** `id_funcionario` continua sendo o funcionário que abriu a OS, derivado de `$auth.id → user.id_funcionario`. O mecânico que executa o serviço fica em um campo novo, `id_mecanico`.
- O cliente da OS é derivado da moto no momento da abertura e gravado como fotografia (`id_cliente`), preservando o histórico mesmo se a moto mudar de dono.
- Máquina de estados:

  | De | Para | Exigências |
  | --- | --- | --- |
  | `ABERTA` | `EM_ANDAMENTO` | — |
  | `ABERTA` | `CANCELADA` | motivo obrigatório |
  | `EM_ANDAMENTO` | `CONCLUIDA` | — |
  | `EM_ANDAMENTO` | `CANCELADA` | motivo obrigatório |
  | `CONCLUIDA` / `CANCELADA` | qualquer | rejeitado (estado final) |

  `ABERTA → CONCLUIDA` direto é rejeitado: o serviço precisa ter sido iniciado.
- Cada transição grava uma linha em `historico_status_os` com status anterior, novo status, funcionário autenticado, data e observação.
- Transições usam controle otimista: o cliente informa o status que está vendo, e o Xano rejeita a operação se a OS tiver mudado nesse meio-tempo.
- Nesta Change, as OS ficam sem itens editáveis. Itens e baixa de estoque são a Change 7, e a transação financeira `ORDEM_SERVICO` fica para uma Change posterior.

## Escopo

### Xano

- Evoluir `ordens_servico` com campos anuláveis (compatíveis com registros antigos): `id_cliente`, `id_mecanico`, `tipo_servico` (`PREVENTIVA` | `CORRETIVA`), `descricao_problema`, `quilometragem`, `data_inicio`, `data_encerramento` e `motivo_cancelamento`.
- Criar a tabela `historico_status_os`.
- Reescrever `POST ordens_servico` (abertura) em `db.transaction`: valida moto e cliente ativos, mecânico ativo do tipo `MECANICO`, ausência de outra OS em aberto para a mesma moto (D5); grava a OS `ABERTA` e a primeira linha de histórico.
- Criar `POST ordens_servico/{id}/status` para as transições, com validação centralizada na função `Oficina/validar_transicao_os`.
- Reescrever `GET ordens_servico` com dados enriquecidos (cliente, moto, placa, autor, mecânico) e filtros opcionais por `status` e `id_moto_cliente`.
- Reescrever `GET ordens_servico/{id}` com detalhe, histórico de status e itens (somente leitura).
- Criar `GET oficina/mecanicos`, que lista id e nome dos mecânicos ativos para a seleção do responsável sem expor o cadastro de funcionários.
- Bloquear `PUT`, `PATCH` e `DELETE ordens_servico/{id}` e as mutações de `itens_ordem_servico` (D6).

### Python

- Criar `Projeto_HarleyStore/services/oficina.py` com os DTOs de abertura, transição, resumo, detalhe, histórico, item e mecânico.
- Adicionar ao `XanoClient`: `list_ordens_servico`, `get_ordem_servico`, `abrir_ordem_servico`, `transicionar_ordem_servico` e `list_mecanicos`.

### Reflex

- Criar `oficina_state.py` e `oficina_pages.py` e substituir o placeholder de `/workshop`.
- Tabela de OS com filtro por status, busca, paginação e estados de carregamento, vazio e erro.
- Modal de abertura: cliente → moto (somente motos ativas do cliente) → mecânico responsável, tipo de serviço, descrição e quilometragem.
- Modal de detalhe: dados da OS, linha do tempo de status, itens (leitura), histórico de OS da mesma moto e ações de transição permitidas.
- `ROUTE_ROLES["/workshop"]` passa a incluir `VENDEDOR` (somente leitura); criação e transição apenas para `GERENTE` e `MECANICO`.
- `on_load` com `restore_session` e erros via `feedback.error_feedback` e `AuthState._xano_error_response`.

### Testes e documentação

- Testes de DTO, cliente HTTP, regras puras do estado, eventos do estado, guard de rota e contratos XanoScript; cenários de integração opcionais.
- Atualizar `docs/domain-model.md`, `docs/xano-api-client.md` e `openspec/specs/` no Archive.

## Matriz de acesso

| Operação | GERENTE | MECANICO | VENDEDOR |
| --- | --- | --- | --- |
| Consultar OS, detalhe e histórico por moto | sim | sim | sim |
| Abrir OS | sim | sim | não |
| Iniciar, concluir ou cancelar OS | sim | sim | não |
| Editar ou excluir OS diretamente | não | não | não |
| Listar mecânicos para seleção | sim | sim | não |

## Fora do escopo

- Inclusão, edição ou remoção de itens de OS e qualquer movimentação de estoque (Change 7).
- Valor de mão de obra, total da OS e transação financeira `ORDEM_SERVICO`.
- Edição de descrição, tipo ou responsável depois da abertura.
- Reabertura de OS encerrada.
- Notificações ao cliente, agenda e orçamento.
- Paginação server-side.

## Critérios de aceite

- Uma OS aberta por `GERENTE` ou `MECANICO` nasce `ABERTA`, com `data_abertura` do servidor, `id_funcionario` do usuário autenticado e `id_cliente` igual ao dono atual da moto, mesmo que o payload envie outros valores.
- A abertura é rejeitada para moto ou cliente inativos ou inexistentes, mecânico inativo ou que não seja do tipo `MECANICO`, descrição vazia, tipo de serviço inválido, quilometragem negativa ou moto com OS `ABERTA`/`EM_ANDAMENTO`.
- Todas as transições da tabela são aceitas e as demais são rejeitadas com `400` e mensagem legível, sem alterar a OS nem gravar histórico.
- Cancelar sem motivo é rejeitado.
- Uma transição enviada com um `status_atual` diferente do status gravado é rejeitada sem efeito.
- Cada abertura e cada transição aceita gera exatamente uma linha em `historico_status_os`, com o funcionário autenticado.
- `data_inicio` é preenchida ao iniciar; `data_encerramento` ao concluir ou cancelar.
- `PUT`, `PATCH` e `DELETE ordens_servico/{id}` e as mutações de `itens_ordem_servico` respondem `403`.
- O vendedor acessa `/workshop` e o detalhe, mas não vê as ações; chamadas forjadas de abertura ou transição recebem `403`.
- O histórico da moto lista todas as OS dela, da mais recente para a mais antiga.
- Após F5 em `/workshop`, a sessão é restaurada e o filtro volta a "Todas".
- Suíte automatizada, `py_compile`, `reflex compile --dry` e validação XanoScript executados antes do Archive.

## Dependências

- Saneamento pré-Change 6 publicado no Xano (`--sync`) e integração configurada, idealmente com a suíte de integração executada.
- Motos de clientes, clientes e ao menos um funcionário `MECANICO` ativos para teste.

## Decisões para validação

- **D1 — Mecânico responsável:** campo novo `id_mecanico`, obrigatório na abertura e restrito a funcionários ativos do tipo `MECANICO`. Quando quem abre é um mecânico e não informa outro, ele próprio é o responsável. *Recomendado.*
- **D2 — Cliente como fotografia:** o cliente vem da moto no servidor e é gravado em `id_cliente`. A UI só usa o cliente para filtrar as motos. *Recomendado.*
- **D3 — Campos da abertura:** `tipo_servico` e `descricao_problema` obrigatórios; `quilometragem` opcional (`>= 0`). *Recomendado.*
- **D4 — `ABERTA → CANCELADA`:** permitido, com motivo obrigatório, assim como `EM_ANDAMENTO → CANCELADA`. `ABERTA → CONCLUIDA` proibido. *Recomendado.*
- **D5 — Uma OS em aberto por moto:** rejeitar nova abertura se a moto já tiver OS `ABERTA` ou `EM_ANDAMENTO`. *Recomendado.*
- **D6 — Itens bloqueados até a Change 7:** as mutações de `itens_ordem_servico` passam a responder `403`, para impedir itens gravados sem baixa de estoque; a leitura continua liberada. *Recomendado.*
- **D7 — Quem transiciona:** qualquer `GERENTE` ou `MECANICO` pode iniciar, concluir ou cancelar qualquer OS, e não só as próprias, conforme o pedido. *Confirmar.*
- **D8 — Endpoint de mecânicos:** um `GET oficina/mecanicos` mínimo (id e nome) para `MECANICO`/`GERENTE`, em vez de abrir `GET funcionarios`, que continua restrito ao gerente. *Recomendado.*

## Resultado aplicado

Decisões D1 a D8 aprovadas integralmente.

- `ordens_servico` recebeu `id_cliente`, `id_mecanico`, `tipo_servico`, `descricao_problema`, `quilometragem`, `data_inicio`, `data_encerramento` e `motivo_cancelamento`, todos anuláveis, com índices novos.
- Nova tabela `historico_status_os`, com índice único `(id_os, status_anterior)`.
- `POST ordens_servico`: abertura transacional com as validações de moto, cliente, mecânico e OS em aberto, autoria pelo JWT, cliente vindo da moto e histórico inicial.
- `POST ordens_servico/{id}/status`: máquina de estados em `Oficina/validar_transicao_os`, controle por `status_atual`, histórico e datas de início e encerramento.
- Leituras enriquecidas (`GET ordens_servico` com filtros `status` e `id_moto_cliente`; `GET ordens_servico/{id}` via `Oficina/detalhe_os`) e o endpoint mínimo `GET oficina/mecanicos`.
- `PUT`/`PATCH`/`DELETE` de OS e as mutações de itens de OS bloqueados com `403`.
- DTOs em `services/ordens_servico.py` e cinco métodos novos no `XanoClient`.
- `/workshop` com filtros por status com contadores, busca, paginação, abertura (cliente → moto → mecânico), detalhe com linha do tempo, itens, histórico da moto e transições com confirmação e motivo.
- `ROUTE_ROLES["/workshop"]` aberto aos três perfis; ações restritas a `GERENTE`/`MECANICO`.
- A suíte passou de 100 para 146 testes.

### Notas de implementação

- **Controle de concorrência.** O design previa um compare-and-set com `db.bulk.patch` e `where`. A gramática oficial do XanoScript (`@xano/xanoscript-language-server`) mostra que `db.bulk.patch` e `db.bulk.update` aceitam apenas `items`, sem `where`, apesar da documentação. A proteção foi implementada assim:
  1. pré-checagem `$os.status == $input.status_atual` (conflito comum, mensagem clara);
  2. dentro da transação, o histórico é gravado **antes** da OS; como a máquina de estados não tem ciclos, cada OS sai de cada status uma única vez, e o índice único `(id_os, status_anterior)` faz a segunda transição concorrente falhar no banco e desfazer tudo;
  3. `try_catch` converte essa falha em `400` legível.
- **Nomes de autor e mecânico na lista:** resolvidos com uma única consulta a `funcionarios` e `find` por linha (alternativa prevista no design), sem depender de dois `join` na mesma tabela. No detalhe, `db.get` individuais.
- **Nomes de arquivos:** conforme a solicitação do Apply, `services/ordens_servico.py`, `workshop_state.py` e `workshop_pages.py` (o design citava `oficina*`); testes em `test_ordens_servico.py`, `test_workshop_state.py` e `test_ordens_servico_contracts.py`.
- **Campos:** mantidos `data_encerramento` (cobre conclusão e cancelamento) e `status_atual` (o "expected status" do controle otimista), conforme o design aprovado.
- **Reflex:** `AuthState` passou a guardar `employee_id` para pré-selecionar o mecânico; `can_workshop` foi removido por falta de uso; os formatadores de data e moeda foram extraídos para `formatting.py` e são compartilhados por entradas e oficina.
- **Evidência em Xano real:** com o `.env` do workspace, `test_public_surface_is_closed` passou contra o backend publicado, confirmando o saneamento pré-Change 6 em produção. Os testes de OS dependem do push desta Change e de credenciais por perfil.

## Status

Aplicada, verificada e arquivada em 2026-09-25.

- `python -m unittest discover -s tests`: 146 testes; 126 executados e aprovados, 20 de integração ignorados por falta de credenciais de perfil (`XANO_TEST_*`).
- `python -m py_compile`: 36 módulos, OK.
- `reflex compile --dry`: OK.
- Validador XanoScript (`@xano/developer-mcp`): 105 arquivos, 0 erros.

Pendente fora do repositório: publicar com `xano workspace push -d ./xano` (alterações aditivas) e executar a suíte de integração com credenciais de teste e `XANO_TEST_ALLOW_WRITES=true`.
