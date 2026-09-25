# Design: ordens de serviço — abertura, máquina de estados e oficina

## Visão geral

```text
/workshop (OficinaState)
  ├─ abrir OS ─────► XanoClient.abrir_ordem_servico ─► POST ordens_servico
  │                                                    enforce_role(MECANICO) → db.transaction {
  │                                                      valida moto/cliente/mecânico/OS em aberto
  │                                                      add OS(ABERTA) → add histórico(null→ABERTA) }
  ├─ transicionar ─► XanoClient.transicionar_ordem_servico ─► POST ordens_servico/{id}/status
  │                                                    enforce_role(MECANICO) → validar_transicao_os
  │                                                    → db.transaction { compare-and-set do status
  │                                                      → add histórico }
  └─ consultar ───► list_ordens_servico / get_ordem_servico ─► GET (ALL), enriquecidos
```

Toda regra de estado vive no Xano. O Reflex replica a tabela de transições só para decidir quais botões exibir e para validar antes do envio.

## Modelo de dados (Xano)

### `ordens_servico` (evolução)

Os campos novos são anuláveis e opcionais na tabela (`tipo? campo?`) para não invalidar OS existentes. A obrigatoriedade fica no input do endpoint. Todos são aditivos, então o push parcial basta.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id_moto_cliente` | int → `motos_clientes` | existente |
| `id_funcionario` | int → `funcionarios` | existente; autor da abertura, derivado do JWT |
| `data_abertura` | timestamp | existente; `now` do servidor |
| `status` | enum | existente; nasce `ABERTA`; muda só pelo endpoint de transição |
| `id_cliente` | int? → `clientes` | **novo**; dono da moto no momento da abertura (D2) |
| `id_mecanico` | int? → `funcionarios` | **novo**; responsável técnico (D1) |
| `tipo_servico` | enum? `PREVENTIVA`, `CORRETIVA` | **novo** (D3) |
| `descricao_problema` | text? `trim` | **novo** (D3) |
| `quilometragem` | int? `min:0` | **novo** (D3) |
| `data_inicio` | timestamp? | **novo**; preenchido em `ABERTA → EM_ANDAMENTO` |
| `data_encerramento` | timestamp? | **novo**; preenchido em `CONCLUIDA` ou `CANCELADA` |
| `motivo_cancelamento` | text? `trim` | **novo**; obrigatório ao cancelar |

Índices novos: `btree (id_cliente)`, `btree (id_mecanico)`, `btree (data_abertura desc)`. `id_moto_cliente` e `status` já estão indexados.

### `historico_status_os` (nova)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | int | PK |
| `id_os` | int → `ordens_servico` | obrigatório |
| `status_anterior` | enum? (quatro status) | `null` na abertura |
| `status_novo` | enum (quatro status) | obrigatório |
| `id_funcionario` | int → `funcionarios` | do JWT |
| `created_at` | timestamp | `now` |
| `observacao` | text? `trim` | motivo do cancelamento ou nota da transição |

Índices: `btree (id_os)`, `btree (created_at desc)`. A tabela é só de inserção: não terá endpoints de escrita próprios.

## Contratos HTTP

### `POST ordens_servico` — abertura (`MECANICO`, que inclui `GERENTE`)

Requisição:

```json
{
  "id_moto_cliente": 12,
  "id_mecanico": 4,
  "tipo_servico": "CORRETIVA",
  "descricao_problema": "Ruído na embreagem ao trocar de marcha.",
  "quilometragem": 18350
}
```

- O input declara somente esses campos (sem `dblink`); `status`, `data_abertura`, `id_funcionario` e `id_cliente` enviados são ignorados.
- `id_mecanico` é opcional no input. Ausente, vale o funcionário autenticado se ele for `MECANICO`; se for `GERENTE`, a abertura é rejeitada com "Informe o mecânico responsável." (D1).

Validações (todas `inputerror`/400, dentro de `db.transaction`):

| Regra | Mensagem |
| --- | --- |
| moto inexistente ou `ativo = false` | "Moto do cliente inativa ou inexistente." |
| cliente da moto inexistente ou inativo | "Cliente da moto inativo ou inexistente." |
| mecânico inexistente, inativo ou tipo ≠ `MECANICO` | "Mecânico responsável inválido ou inativo." |
| moto com OS `ABERTA` ou `EM_ANDAMENTO` (D5) | "Esta moto já possui uma OS em aberto (nº X)." |
| descrição vazia | validação de plataforma antes do stack (campo `text` obrigatório) |

Gravação: `db.add ordens_servico` com `status: "ABERTA"`, `data_abertura: now`, `id_funcionario: $auth_user.id_funcionario` e `id_cliente: $moto.id_cliente`, seguido de `db.add historico_status_os` (`null → ABERTA`). Resposta: `OrdemServicoDetalhe`.

### `POST ordens_servico/{ordens_servico_id}/status` — transição (`MECANICO`)

```json
{"status_atual": "ABERTA", "status_novo": "EM_ANDAMENTO", "observacao": null}
```

Fluxo:

1. `enforce_role` `MECANICO` e resolução de `$auth_user.id_funcionario`.
2. `function.run "Oficina/validar_transicao_os"` com `status_atual`, `status_novo` e `observacao`; lança `inputerror` para transição fora da tabela, estado final ou cancelamento sem motivo.
3. `db.transaction`:
   - monta `$dados` com `status`, e `data_inicio` / `data_encerramento` / `motivo_cancelamento` conforme o destino;
   - `db.bulk.patch ordens_servico { where = id == $input.ordens_servico_id && status == $input.status_atual; data = $dados } as $alterados`;
   - `precondition ($alterados == 1)` → "A OS foi alterada por outro usuário ou não existe. Atualize e tente novamente.";
   - `db.add historico_status_os`.
4. Resposta: `OrdemServicoDetalhe` atualizado.

> **Implementado de outra forma:** `db.bulk.patch` não aceita `where` na gramática oficial do XanoScript. A proteção passou a ser a pré-checagem de `status_atual` somada ao índice único `(id_os, status_anterior)` em `historico_status_os`, gravado antes da OS na mesma transação. Detalhes em "Notas de implementação" na proposta.

O `bulk.patch` com o status esperado no `where` é um *compare-and-set* executado pelo banco: duas transições simultâneas a partir do mesmo status não podem ambas vencer, o que evita o risco de atualização perdida aceito na D4 da Change 5. No Apply, confirmar que `db.bulk.patch` devolve a contagem de linhas alteradas; se não devolver, usar `db.bulk.update` com `data` montado por `conditional`.

### `Oficina/validar_transicao_os` (função)

Entrada `status_atual`, `status_novo`, `observacao?`. Tabela única de transições:

```text
ABERTA        → EM_ANDAMENTO | CANCELADA
EM_ANDAMENTO  → CONCLUIDA    | CANCELADA
CONCLUIDA     → (nenhum)
CANCELADA     → (nenhum)
CANCELADA exige observacao não vazia
```

Mensagens: "Transição de status inválida: A → B.", "OS encerrada não pode ser reaberta ou alterada.", "Informe o motivo do cancelamento."

### `Oficina/detalhe_os` (função)

Monta `OrdemServicoDetalhe` e é reutilizada por abertura, transição e `GET ordens_servico/{id}`: OS com nomes de cliente, autor e mecânico, placa e modelo da moto, `historico` (ordenado por `created_at`, com nome do funcionário) e `itens` (com `codigo` e `nome_produto`, somente leitura).

### `GET ordens_servico` — lista (`ALL`)

Input opcional `status` (enum) e `id_moto_cliente` (int), aplicados com operadores nulo-seguros (`==?`). Ordenação por `data_abertura` decrescente. Cada linha traz `nome_cliente`, `placa`, `modelo`, `nome_funcionario` e `nome_mecanico`. Também atende o histórico por moto (`?id_moto_cliente=12`).

### `GET ordens_servico/{id}` — detalhe (`ALL`)

`function.run "Oficina/detalhe_os"`; `404` quando a OS não existe.

### `GET oficina/mecanicos` (`MECANICO`)

`[{id, nome_funcionario}]` dos funcionários `tipo = MECANICO` e ativos. Não expõe contato, cargo nem outros tipos (D8).

### Endpoints bloqueados

`PUT`, `PATCH` e `DELETE ordens_servico/{id}` e `POST`, `PUT`, `PATCH` e `DELETE itens_ordem_servico[/{id}]` passam a `enforce_role` + `precondition (false)` com `accessdenied`, preservando rota e `guid`, no mesmo padrão da Change 5. `GET itens_ordem_servico[/{id}]` continua `ALL`.

### Joins com a mesma tabela

Autor e mecânico vêm ambos de `funcionarios`. O Apply deve confirmar no validador e no Xano real que o `join` aceita dois aliases para a mesma tabela (`autor`, `mecanico`). Se não aceitar, os nomes são resolvidos por `db.get` no detalhe e por um mapa `id → nome` montado com uma única consulta a `funcionarios` na lista, evitando N+1.

## Cliente Python

### DTOs — `Projeto_HarleyStore/services/oficina.py`

```python
StatusOS = Literal["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
TipoServico = Literal["PREVENTIVA", "CORRETIVA"]

TRANSICOES_OS: dict[str, frozenset[str]]   # espelho da função Xano

class OrdemServicoCreate(BaseModel):        # str_strip_whitespace
    id_moto_cliente: int = Field(gt=0)
    id_mecanico: int | None = Field(default=None, gt=0)
    tipo_servico: TipoServico
    descricao_problema: str = Field(min_length=1, max_length=2000)
    quilometragem: int | None = Field(default=None, ge=0)

class TransicaoStatusOS(BaseModel):
    status_atual: StatusOS
    status_novo: StatusOS
    observacao: str | None = None
    # model_validator: transição presente em TRANSICOES_OS; CANCELADA exige observacao

class OrdemServicoResumo(BaseModel):        # extra="ignore"; campos novos opcionais (legado)
    id, status, id_moto_cliente, data_abertura
    tipo_servico, descricao_problema, data_inicio, data_encerramento
    id_cliente, nome_cliente, placa, modelo
    id_funcionario, nome_funcionario, id_mecanico, nome_mecanico

class HistoricoStatusOS(BaseModel): status_anterior, status_novo, id_funcionario, nome_funcionario, created_at, observacao
class ItemOrdemServico(BaseModel): id, id_produto, codigo, nome_produto, quantidade, valor_total_item
class OrdemServicoDetalhe(OrdemServicoResumo): quilometragem, motivo_cancelamento, historico, itens
class Mecanico(BaseModel): id, nome_funcionario
```

### `XanoClient`

```python
def list_ordens_servico(self, *, status: str | None = None, id_moto_cliente: int | None = None) -> list[OrdemServicoResumo]
def get_ordem_servico(self, os_id: int) -> OrdemServicoDetalhe
def abrir_ordem_servico(self, ordem: OrdemServicoCreate) -> OrdemServicoDetalhe
def transicionar_ordem_servico(self, os_id: int, transicao: TransicaoStatusOS) -> OrdemServicoDetalhe
def list_mecanicos(self) -> list[Mecanico]
```

Os filtros da lista vão como query string e são omitidos quando `None`. A abertura usa `model_dump(mode="json", exclude_none=True)`, para que `id_mecanico` ausente não seja enviado como `null`.

## Reflex

### Arquivos

| Arquivo | Papel |
| --- | --- |
| `Projeto_HarleyStore/oficina_state.py` (novo) | `OficinaState(AuthState)` e funções puras de regra |
| `Projeto_HarleyStore/oficina_pages.py` (novo) | página `/workshop`, tabela, filtros e modais |
| `Projeto_HarleyStore/auth.py` | `ROUTE_ROLES["/workshop"] = ALL_ROLES`; remove `can_workshop` se ficar sem uso |
| `Projeto_HarleyStore/Projeto_HarleyStore.py` | `/workshop` usa `oficina_page` com `on_load=[AuthState.restore_session, OficinaState.load_ordens]` |
| `Projeto_HarleyStore/listing.py` | reutilizado (busca, paginação, opções de select) |
| `Projeto_HarleyStore/feedback.py` | reutilizado (mensagens) |

### Funções puras (testáveis sem Reflex)

- `can_operate_os(role)`: `GERENTE` ou `MECANICO`.
- `allowed_transitions(status, role) -> list[str]`: destinos permitidos por `TRANSICOES_OS`, vazio para vendedor ou estado final.
- `filter_by_status(rows, status)`: `"TODAS"` não filtra.
- `status_counts(rows) -> dict[str, str]`: contagens para os filtros.
- `build_abertura_payload(cliente, moto, mecanico, tipo, descricao, km, role)` → `OrdemServicoCreate` ou `OficinaFormError` com mensagem em português.
- `build_transicao_payload(status_atual, status_novo, observacao)` → `TransicaoStatusOS` ou `OficinaFormError`.
- `os_row`, `historico_row`, `item_row`: DTO → `dict[str, str]` legível (datas `dd/mm/aaaa hh:mm`, rótulos de status e tipo).
- `motos_do_cliente(motos, cliente_id)`: somente motos ativas do cliente selecionado.

### `OficinaState`

Estado:

- lista: `ordens`, `status_filter` (`"TODAS"`), `search_text`, `current_page`, `page_size`, `list_error`, `is_loading_list`;
- detalhe: `detail_open`, `detalhe`, `detalhe_historico`, `detalhe_itens`, `historico_moto`, `is_loading_detail`;
- abertura: `form_open`, `form_error`, `cliente`, `moto`, `mecanico`, `tipo_servico`, `descricao_problema`, `quilometragem`, `cliente_options`, `motos_cache`, `mecanico_options`, `is_saving`;
- transição: `transition_target`, `transition_note`, `transition_error`, `is_transitioning`.

Computed vars: `visible_rows`, `total_pages`, `can_operate`, `status_counts`, `moto_options` (derivado de `cliente` e `motos_cache`), `available_transitions` (do status em `detalhe` e do cargo), `is_busy`.

Eventos e regras:

- `load_ordens`: sem sessão ou rota não permitida, retorna sem chamar o Xano; em erro, limpa `ordens` e preenche `list_error`; `401` passa por `_xano_error_response`.
- `set_status_filter`, `set_search_text`, `previous_page`, `next_page`: voltam à página 1 quando o filtro muda.
- `open_detail(id)`: carrega o detalhe e depois `list_ordens_servico(id_moto_cliente=...)` para o histórico da moto, excluindo a OS atual.
- `open_create`: exige `can_operate`; carrega clientes ativos, motos de clientes e `list_mecanicos()`; um mecânico vem pré-selecionado como responsável.
- `set_cliente` limpa `moto`; `save_os` valida com `build_abertura_payload`, bloqueia reentrada com `operation_is_blocked`, fecha o modal e recarrega a lista; em `400`, mantém o formulário aberto com a mensagem do Xano.
- `start_transition(target)` abre a confirmação; `confirm_transition` envia `build_transicao_payload`, recarrega o detalhe e a lista; em `400` (inclusive conflito de status), mostra a mensagem e recarrega o detalhe para exibir o status real.

### Interface

- Cabeçalho "Oficina" com o botão "Nova OS" (somente `can_operate`).
- Filtro por status em controle segmentado: Todas · Abertas · Em andamento · Concluídas · Canceladas, com contagens.
- Busca por número, cliente, placa, modelo, mecânico ou descrição.
- Tabela: Nº, Abertura, Cliente, Moto (placa · modelo), Tipo, Mecânico, Status (badge), Detalhes.
- Cores dos badges: `ABERTA` laranja, `EM_ANDAMENTO` azul, `CONCLUIDA` verde, `CANCELADA` cinza, dentro do tema escuro.
- Modal de abertura: select de cliente → select de moto (desabilitado sem cliente) → select de mecânico → tipo (Preventiva/Corretiva) → descrição (textarea) → quilometragem.
- Modal de detalhe: cabeçalho com número e badge, dados da moto e do cliente, descrição, linha do tempo de status, itens (tabela somente leitura, com o aviso de que a inclusão virá na próxima etapa), histórico da moto e botões de transição disponíveis.
- Confirmação de transição: texto do efeito; textarea de motivo obrigatória quando o destino é `CANCELADA`.

## Cenários de aceite

### Abertura

- **DADO** um mecânico autenticado e uma moto ativa de cliente ativo sem OS em aberto
- **QUANDO** abrir uma OS corretiva com descrição
- **ENTÃO** a OS DEVE nascer `ABERTA`, com o mecânico como autor e responsável e o cliente da moto
- **E** o histórico DEVE ter uma linha `null → ABERTA`

- **DADO** um payload com `status = "CONCLUIDA"`, `id_funcionario` e `id_cliente` de terceiros
- **QUANDO** a OS for aberta
- **ENTÃO** esses valores DEVEM ser ignorados

- **DADO** uma moto com OS `EM_ANDAMENTO`
- **QUANDO** abrir outra OS para ela
- **ENTÃO** a resposta DEVE ser `400` e nenhuma OS DEVE ser criada

- **DADO** um gerente que não informa o mecânico
- **QUANDO** abrir a OS
- **ENTÃO** a resposta DEVE ser `400` "Informe o mecânico responsável."

### Transições

- **DADO** uma OS `ABERTA`
- **QUANDO** iniciar, e depois concluir
- **ENTÃO** `data_inicio` e `data_encerramento` DEVEM ser preenchidas e o histórico DEVE ter três linhas

- **DADO** uma OS `ABERTA`
- **QUANDO** tentar `CONCLUIDA` direto
- **ENTÃO** a resposta DEVE ser `400` e a OS NÃO DEVE mudar

- **DADO** uma OS `CONCLUIDA` ou `CANCELADA`
- **QUANDO** tentar qualquer transição
- **ENTÃO** a resposta DEVE ser `400` "OS encerrada não pode ser reaberta ou alterada."

- **DADO** uma OS `EM_ANDAMENTO`
- **QUANDO** cancelar sem motivo
- **ENTÃO** a resposta DEVE ser `400`; com motivo, DEVE ir para `CANCELADA` e gravar `motivo_cancelamento`

- **DADO** dois usuários vendo a mesma OS `ABERTA`
- **QUANDO** um a inicia e o outro tenta cancelá-la informando `status_atual = ABERTA`
- **ENTÃO** a segunda operação DEVE ser rejeitada sem efeito, e a UI DEVE mostrar o status real

### Acesso

- **DADO** um vendedor autenticado
- **QUANDO** acessar `/workshop`
- **ENTÃO** DEVE ver a lista e o detalhe, sem "Nova OS" e sem botões de transição
- **E** `POST ordens_servico` e `POST ordens_servico/{id}/status` forjados DEVEM receber `403`

- **DADO** qualquer perfil
- **QUANDO** chamar `PATCH`/`DELETE ordens_servico/{id}` ou `POST itens_ordem_servico`
- **ENTÃO** a resposta DEVE ser `403`

### Histórico por moto

- **DADO** uma moto com três OS
- **QUANDO** abrir o detalhe de uma delas
- **ENTÃO** as outras duas DEVEM aparecer no histórico da moto, da mais recente para a mais antiga

## Plano de testes

| Arquivo | Cobertura |
| --- | --- |
| `tests/test_oficina.py` (novo) | DTOs: tipo e status inválidos, descrição vazia ou só espaços, km negativa, `id_mecanico` opcional; `TransicaoStatusOS` para as 16 combinações de status e o cancelamento sem motivo. Cliente: caminhos, verbos, query string dos filtros, payload de abertura sem `status`/`id_funcionario`/`id_cliente`/`data_abertura`, parsing de resumo e detalhe legados (campos nulos), `400` com mensagem, `403`, `404`. |
| `tests/test_oficina_state.py` (novo) | Funções puras (`allowed_transitions` por cargo e status, `filter_by_status`, `status_counts`, `motos_do_cliente`, `build_*_payload` com mensagens em português, formatação de linhas). Eventos com a árvore real do Reflex: carga sem sessão não chama o Xano; vendedor não abre OS nem transiciona; reentrada bloqueada; sucesso fecha o modal e recarrega; `400` mantém o modal com mensagem; conflito de status recarrega o detalhe; `401` limpa a sessão. |
| `tests/test_oficina_contracts.py` (novo) | XanoScript: abertura com `required_role: "MECANICO"`, `db.transaction`, `status: "ABERTA"`, `$auth_user.id_funcionario`, `id_cliente` vindo da moto, ausência de `$input.status`, `$input.id_funcionario`, `$input.id_cliente` e `dblink`; transição com `validar_transicao_os`, compare-and-set com `status == $input.status_atual` e histórico; a função contém a tabela de transições; endpoints bloqueados; `GET` com `ALL`; `oficina/mecanicos` só com id e nome; schema com campos anuláveis e a nova tabela. |
| `tests/test_authentication.py` | `/workshop` permitido aos três perfis. |
| `tests/test_hardening_contracts.py` e `tests/test_security_contracts.py` | Retirar `ordens_servico_id_PUT`/`PATCH` das listas de autoria (passam a ser bloqueados) e incluir o novo endpoint de transição na verificação de autoria. |
| `tests/test_integration_xano.py` | Leitura: lista e detalhe por perfil; vendedor recebe `403` ao abrir OS. Escrita (`XANO_TEST_ALLOW_WRITES`): abrir, iniciar, concluir; `ABERTA → CONCLUIDA` rejeitado; conflito de `status_atual`; cancelamento sem motivo. As OS de teste ficam encerradas como `CANCELADA`. |

Verificação: `python -m unittest discover -s tests`, `python -m py_compile`, `reflex compile --dry` e o validador XanoScript.

## Riscos

| Risco | Mitigação |
| --- | --- |
| `db.bulk.patch` não retornar a contagem ou o `where` composto não se comportar como compare-and-set | Validar no Apply (validador e Xano real); alternativa com `db.bulk.update` |
| Join duplo em `funcionarios` não suportado | Mapa `id → nome` com uma consulta |
| Aberturas simultâneas para a mesma moto (D5) passarem ambas | Janela pequena; risco aceito e documentado, como a D4 da Change 5 |
| OS antigas com campos nulos ou status fora do fluxo | DTOs de leitura tolerantes; transições continuam válidas a partir do status gravado |
| Campo `text` obrigatório rejeita `""` antes do stack com mensagem de plataforma | Validação prévia no DTO e no formulário |
| Lista inteira carregada no navegador | Filtros `status` e `id_moto_cliente` já no servidor, prontos para uma paginação server-side futura |
