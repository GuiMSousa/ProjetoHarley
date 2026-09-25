# Design: itens da OS com baixa atômica de estoque e integridade financeira

## Visão geral

```text
/workshop · detalhe da OS (WorkshopState)
  ├─ incluir item ──► XanoClient.adicionar_item_ordem_servico ─► POST ordens_servico/{id}/itens
  │                     enforce_role(MECANICO) → pré-checagens (mensagens claras)
  │                     → db.transaction {
  │                         trava a OS (atualizado_em) → relê status
  │                         PECA: add item (preço do produto) → Estoque/movimentar_estoque(SAIDA_OS)
  │                         SERVICO: add item (valor informado)
  │                         Oficina/totais_os → grava totais na OS }
  ├─ remover item ──► XanoClient.remover_item_ordem_servico ─► DELETE ordens_servico/{id}/itens/{item_id}
  │                     … trava a OS → relê status e item
  │                     → se estoque_baixado: movimentar_estoque(ESTORNO_OS) → del item → totais }
  ├─ cancelar OS ───► transicionar_ordem_servico ─► POST ordens_servico/{id}/status (existente)
  │                     … histórico → patch OS (trava) → para cada peça baixada: ESTORNO_OS }
  └─ catálogo ──────► XanoClient.list_produtos ─► GET produtos (existente, ALL)

POST entrada_mercadoria (existente) ─► para cada item: Estoque/movimentar_estoque(ENTRADA)
```

As regras vivem no Xano. O Reflex valida antes de enviar, pela tipagem do DTO e pelo saldo do catálogo, só para dar retorno imediato. A decisão final é sempre do servidor.

`Estoque/movimentar_estoque` passa a ser o **único** código que altera `produtos.estoque_qtd` depois da criação do produto.

## Modelo de dados (Xano)

### `itens_ordem_servico` (evolução)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id_os` | int → `ordens_servico` | existente |
| `id_produto` | **int?** → `produtos` | existente, **relaxado para anulável** (D2); obrigatório para `PECA`, nulo para `SERVICO` |
| `quantidade` | int `min:1` | existente |
| `valor_total_item` | decimal `min:0.01` | existente; `quantidade × valor_unitario`, calculado no Xano |
| `tipo_item` | enum? `PECA`, `SERVICO` | **novo**; nulo em itens legados, lido como `PECA` (D10) |
| `descricao` | text? `trim` | **novo**; obrigatório para `SERVICO` |
| `valor_unitario` | decimal? `min:0.01` | **novo**; fotografia de `preco_venda` (`PECA`) ou valor informado (`SERVICO`) |
| `estoque_baixado` | bool? | **novo**; `true` quando a inclusão gerou `SAIDA_OS`; nulo em itens legados |
| `id_funcionario` | int? → `funcionarios` | **novo**; quem incluiu, derivado do JWT |
| `created_at` | timestamp? `=now` | **novo** |

Os índices `id_os` e `id_produto` já existem.

O relaxamento de `id_produto` é a única mudança não aditiva desta Change e exige `xano workspace push -d ./xano --sync`. Por isso a publicação deve partir de um repositório em sincronia com o workspace, como já foi feito no saneamento.

### `ordens_servico` (evolução)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `valor_pecas` | decimal? | **novo**; Σ `valor_total_item` dos itens `PECA` (D8) |
| `valor_servicos` | decimal? | **novo**; Σ `valor_total_item` dos itens `SERVICO` |
| `valor_total` | decimal? | **novo**; `valor_pecas + valor_servicos` |
| `atualizado_em` | timestamp? | **novo**; atualizado no início de toda mutação, para travar a linha (D7) |

Os campos são anuláveis: OS legadas continuam válidas, e a lista as exibe como "—" até a primeira mutação.

### `produtos` (evolução)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `versao_estoque` | int? `min:0` | **novo**; incrementado a cada movimentação; nulo equivale a `0` (D6) |

`POST produtos` e `PUT produtos/{id}` montam `data` campo a campo e não tocam o campo novo. `PATCH produtos/{id}` usa `pick` das chaves recebidas e passa a encadear `|unset:"versao_estoque"`, ao lado do `|unset:"estoque_qtd"` que já existe.

### `movimentacoes_estoque` (nova)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | int | PK |
| `id_produto` | int → `produtos` | obrigatório |
| `tipo` | enum `ENTRADA`, `SAIDA_OS`, `ESTORNO_OS` | obrigatório |
| `quantidade` | int `min:1` | sempre positiva; o sentido vem do `tipo` |
| `saldo_anterior` | int `min:0` | saldo lido na mesma transação |
| `saldo_posterior` | int `min:0` | saldo gravado em `produtos.estoque_qtd` |
| `versao_anterior` | int `min:0` | `produtos.versao_estoque` lida; a gravação usa `versao_anterior + 1` |
| `id_funcionario` | int → `funcionarios` | do JWT |
| `id_entrada` | int? → `entrada_mercadoria` | origem `ENTRADA` |
| `id_os` | int? → `ordens_servico` | origem `SAIDA_OS`/`ESTORNO_OS` |
| `id_item_os` | int? | sem vínculo de tabela, porque o item pode ser removido depois |
| `created_at` | timestamp `=now` | |

Índices:

- `btree|unique (id_produto, versao_anterior)`: o comentário que explica o índice fica **acima** de `index = [`, porque o parser não aceita comentários dentro do array;
- `btree (id_os)`;
- `btree (created_at desc)`.

A tabela só recebe inserções e não tem endpoints de escrita.

## Concorrência

### Estoque: versão por produto (D6)

A garantia é a mesma do histórico de status da Change 6, desta vez com um contador. O `db.bulk.patch` com `where` continua indisponível na gramática.

1. `db.get produtos` lê `estoque_qtd` e `versao_estoque` numa única leitura de linha, o que dá uma fotografia consistente.
2. `db.add movimentacoes_estoque` grava com `versao_anterior = v`.
3. `db.edit produtos` grava o novo saldo e `versao_estoque = v + 1`.

Se duas transações leem a mesma versão `v`, a segunda a inserir `(id_produto, v)` viola o índice único, espera o commit da primeira e falha. Com isso, toda a transação da segunda é desfeita: item, movimento e totais.

Se a segunda transação começar depois do commit da primeira, lê a versão `v + 1` e o saldo já reduzido, e a pré-condição de saldo decide normalmente.

Como `POST entrada_mercadoria` também passa por `movimentar_estoque`, uma entrada e uma baixa simultâneas do mesmo produto se serializam da mesma forma. Isso fecha o risco de sobrescrita aceito na Change 5.

**Ordem de travamento:** a entrada e o cancelamento iteram os produtos em ordem crescente de `id_produto`. Duas transações com vários produtos travam então as linhas na mesma ordem, o que evita deadlock entre, por exemplo, uma entrada de P2 e P1 e o cancelamento de uma OS com P1 e P2.

### OS: trava pela linha (D7)

Inclusão, remoção e transição da mesma OS precisam se excluir mutuamente. Sem isso, uma inclusão concorrente com o cancelamento poderia ver a OS `ABERTA`, baixar a peça e gravar depois que o cancelamento já devolveu os itens que conhecia, e a peça nunca voltaria ao estoque.

- **Inclusão e remoção:** a primeira operação dentro da transação é `db.edit ordens_servico { atualizado_em: now }`. O `UPDATE` trava a linha até o commit, e só então a transação relê `status` (e o item, na remoção) com `db.get`.
- **Transição:** o `db.patch ordens_servico` que já existe passa a incluir `atualizado_em`. No cancelamento, a consulta dos itens a devolver vem **depois** desse `patch`.

| Corrida | Resultado |
| --- | --- |
| Inclusão trava primeiro, cancelamento espera | O item é gravado; o cancelamento relê os itens depois do commit e devolve a peça |
| Cancelamento trava primeiro, inclusão espera | A inclusão relê `CANCELADA` e é rejeitada; nada é gravado |
| Duas remoções do mesmo item | A segunda relê o item, não o encontra e é rejeitada; o estoque volta uma única vez |
| Conclusão e inclusão | Se a conclusão vence, a inclusão relê `CONCLUIDA` e é rejeitada; se a inclusão vence, o item entra antes da conclusão |

**Premissa:** o Xano roda sobre Postgres e cada operação `db.*` é um comando dentro da transação. Em *read committed*, o padrão do Postgres, cada comando vê o que já foi confirmado antes dele, então a releitura depois da trava enxerga o estado real. Se o Xano usar um isolamento mais forte, a segunda transação falha com erro de serialização e é desfeita, o que também é seguro. O Apply valida essa premissa com o teste de integração concorrente (tarefa 0).

### Mensagens dentro da transação

Toda escrita fica em `try_catch`. Uma falha dentro da transação só acontece em corrida, porque as pré-checagens de fora já passaram instantes antes. Por isso o `catch` devolve uma mensagem genérica de conflito: "O estoque ou a OS foram alterados por outra operação. Atualize e tente novamente."

As pré-checagens feitas **fora** da transação dão as mensagens específicas, como saldo insuficiente, produto repetido ou OS encerrada. As mesmas regras são repetidas **dentro** dela como garantia.

No Apply, verificar se `$error.message` preserva o texto de uma `precondition` disparada dentro da transação. Se preservar, o `catch` pode repassá-lo quando o erro não vier do banco, o que é uma melhoria opcional.

> **Implementado:** a melhoria opcional não foi aplicada, porque só é verificável no Xano real. O `catch` usa a mensagem genérica de conflito.

## Funções (Xano)

### `Estoque/movimentar_estoque`

Único ponto de alteração de saldo, e sempre chamado **dentro** da `db.transaction` de quem a invoca.

```text
input:
  int id_produto, enum tipo {ENTRADA, SAIDA_OS, ESTORNO_OS}, int quantidade (min:1)
  int id_funcionario, int? id_entrada?, int? id_os?, int? id_item_os?

db.get produtos (id, codigo, estoque_qtd, versao_estoque, ativo) as $produto
precondition $produto != null                       → "Produto inativo ou inexistente."
SAIDA_OS: precondition $produto.ativo != false        → "Produto inativo ou inexistente."
$saldo_anterior = $produto.estoque_qtd ?? 0
$versao         = $produto.versao_estoque ?? 0
$saldo_posterior = SAIDA_OS ? saldo_anterior - quantidade : saldo_anterior + quantidade
precondition $saldo_posterior >= 0
  → "Saldo insuficiente para <codigo>: disponível <saldo_anterior>, solicitado <quantidade>."
db.add movimentacoes_estoque {…, versao_anterior: $versao, created_at: now} as $movimento
db.edit produtos {estoque_qtd: $saldo_posterior, versao_estoque: $versao + 1}
response = $movimento
```

A verificação de produto ativo vale só para `SAIDA_OS`. Devolver peça a um produto desativado depois da inclusão é permitido, e a `ENTRADA` já valida o produto ativo no próprio endpoint.

### `Oficina/totais_os`

Entrada `os_id`. Consulta os itens da OS e soma `valor_total_item` separando por `tipo_item ?? "PECA"`, com um `foreach`, que é o padrão já usado na entrada. Resposta: `{valor_pecas, valor_servicos, valor_total}`.

É reutilizada:

- pelas mutações, que gravam o resultado na OS;
- por `Oficina/detalhe_os`, que o sobrepõe aos campos gravados. A fonte de verdade são os itens (D8), e isso cobre OS legadas.

### `Oficina/detalhe_os` (alterada)

- Os itens passam a trazer, pela consulta com join que já existe, `tipo_item`, `descricao`, `valor_unitario`, `estoque_baixado` e `created_at`, além de `codigo` e `nome_produto`.
- O detalhe ganha `valor_pecas`, `valor_servicos` e `valor_total`, vindos de `Oficina/totais_os`.

## Contratos HTTP

### `POST ordens_servico/{ordens_servico_id}/itens` — inclusão (`MECANICO`, que inclui `GERENTE`)

Peça:

```json
{"tipo_item": "PECA", "id_produto": 31, "quantidade": 2}
```

Serviço:

```json
{"tipo_item": "SERVICO", "descricao": "Troca do kit de embreagem", "quantidade": 1, "valor_unitario": 380.00}
```

O input declara apenas esses campos, sem `dblink`:

- **Peça:** `valor_unitario` e `descricao` enviados são ignorados.
- **Serviço:** `id_produto` é ignorado.
- **Sempre ignorados:** `valor_total_item`, `estoque_baixado`, `id_funcionario` e totais da OS enviados no payload.

Fluxo:

1. `enforce_role` `MECANICO` e resolução de `$auth_user.id_funcionario`, como na Change 6.
2. Pré-checagens, fora da transação:

   | Regra | Erro |
   | --- | --- |
   | OS inexistente | `404` "Ordem de serviço não encontrada." |
   | OS `CONCLUIDA` ou `CANCELADA` | `400` "OS encerrada não permite alterar itens." |
   | `PECA` sem `id_produto` | `400` "Selecione o produto." |
   | `PECA` com produto inexistente ou inativo | `400` "Produto inativo ou inexistente." |
   | `PECA` com produto já presente na OS (D4) | `400` "Este produto já está na OS. Remova o item para alterar a quantidade." |
   | `PECA` com `quantidade > estoque_qtd` | `400` "Saldo insuficiente para <código>: disponível X, solicitado Y." |
   | `SERVICO` sem descrição (após `trim`) | `400` "Informe a descrição do serviço." |
   | `SERVICO` sem `valor_unitario` | `400` "Informe o valor do serviço." |
   | `quantidade < 1` ou `valor_unitario <= 0` | `400` pela validação do input |

3. `try_catch { db.transaction { … } }`:
   - `db.edit ordens_servico { atualizado_em: now }`, que trava a linha;
   - `db.get ordens_servico` e `precondition` de status editável;
   - **PECA:**
     - `db.get produtos` para ler `preco_venda`;
     - repetir a checagem de produto repetido;
     - `db.add itens_ordem_servico` com `valor_unitario = preco_venda`, `valor_total_item = quantidade × preco_venda`, `estoque_baixado = true`, `id_funcionario` do JWT e `created_at: now`;
     - `function.run "Estoque/movimentar_estoque"` com `SAIDA_OS`, `id_os` e `id_item_os`;
   - **SERVICO:** `db.add itens_ordem_servico` com o valor informado e `estoque_baixado = false`;
   - `function.run "Oficina/totais_os"` e `db.edit ordens_servico` com os três totais;
   - no `catch`, `400` com a mensagem genérica de conflito.
4. Resposta: `function.run "Oficina/detalhe_os"`, o que dá um `OrdemServicoDetalhe` atualizado.

`valor_total_item` é arredondado a duas casas (`|round:2`) antes de gravar.

### `DELETE ordens_servico/{ordens_servico_id}/itens/{item_id}` — remoção (`MECANICO`)

1. `enforce_role` e `$auth_user`.
2. Pré-checagens:
   - OS inexistente: `404`;
   - item inexistente ou de outra OS: `404` "Item não encontrado nesta OS.";
   - OS encerrada: `400` "OS encerrada não permite alterar itens.".
3. `try_catch { db.transaction { … } }`:
   - trava a OS, relê o status e relê o item (`precondition` de existência e de pertencer à OS);
   - se `estoque_baixado == true`, `movimentar_estoque(ESTORNO_OS, quantidade, id_os, id_item_os)`;
   - `db.del itens_ordem_servico`;
   - recalcula e grava os totais.
4. Resposta: `OrdemServicoDetalhe` atualizado.

Serviços e itens legados, com `estoque_baixado` diferente de `true`, são removidos sem movimentar o estoque (D10).

### `POST ordens_servico/{id}/status` (alterado)

- `$dados` passa a incluir `atualizado_em: now` em toda transição.
- Dentro da transação que já existe, depois do `db.patch ordens_servico` e só quando `status_novo == "CANCELADA"`:
  - consulta `itens_ordem_servico` com `id_os == $os` e `estoque_baixado == true`, ordenados por `id_produto`;
  - para cada item, `movimentar_estoque(ESTORNO_OS)`.
- A falha de qualquer devolução desfaz o cancelamento inteiro, e o `catch` que já existe responde `400`.
- Concluir e iniciar não mexem no estoque.
- A ordem "histórico → `patch` → devoluções" preserva a proteção da Change 6: o índice único do histórico continua sendo a primeira gravação.

### `POST entrada_mercadoria` (alterado, contrato inalterado)

- Os itens validados são ordenados por `id_produto` antes do `foreach`.
- O par `db.get produtos` + `db.edit produtos` dá lugar a:
  - `db.get produtos`, só para validar o produto ativo, com a mesma mensagem de hoje;
  - `db.add itens_compra_estoque`, como hoje;
  - `function.run "Estoque/movimentar_estoque"` com `ENTRADA` e `id_entrada`.
- A resposta e as mensagens não mudam. Os testes de contrato de `test_estoque_contracts.py` que procuram `db.edit produtos` e a fórmula de incremento passam a procurar a chamada da função.

### Rotas legadas de itens

`POST itens_ordem_servico` e `PUT`/`PATCH`/`DELETE itens_ordem_servico/{id}` continuam com `precondition (false)` `accessdenied`, com rota e `guid` preservados. A mensagem passa a ser "Use POST/DELETE ordens_servico/{id}/itens." `GET itens_ordem_servico[/{id}]` continua `ALL`.

### `GET ordens_servico` (sem mudança de código)

A consulta devolve todas as colunas da OS, então `valor_total` passa a aparecer na lista sem alteração no endpoint. O teste de contrato só confirma que o campo não é removido.

## Cliente Python

### DTOs — `Projeto_HarleyStore/services/ordens_servico.py`

```python
TipoItemOS = Literal["PECA", "SERVICO"]

class ItemOSCreate(BaseModel):                  # str_strip_whitespace
    tipo_item: TipoItemOS
    id_produto: int | None = Field(default=None, gt=0)
    descricao: str | None = Field(default=None, max_length=200)
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    # model_validator(mode="after"):
    #   PECA    → exige id_produto ("Selecione o produto."); zera descricao e valor_unitario
    #   SERVICO → exige descricao ("Informe a descrição do serviço.") e valor_unitario
    #             ("Informe o valor do serviço."); zera id_produto

class ItemOrdemServico(BaseModel):              # extra="ignore"; legado tolerado
    id: int
    tipo_item: TipoItemOS = "PECA"              # field_validator(before): None → "PECA"
    id_produto: int | None = None
    codigo: str | None = None
    nome_produto: str | None = None
    descricao: str | None = None
    quantidade: int
    valor_unitario: Decimal | None = None
    valor_total_item: Decimal | None = None
    estoque_baixado: bool | None = None
    created_at: datetime | None = None

class OrdemServicoResumo:  + valor_total: Decimal | None = None
class OrdemServicoDetalhe: + valor_pecas: Decimal | None = None
                           + valor_servicos: Decimal | None = None
```

A remoção não tem corpo, porque a OS e o item vão no caminho. Por isso não há DTO de remoção.

### `XanoClient`

```python
def adicionar_item_ordem_servico(self, os_id: int, item: ItemOSCreate) -> OrdemServicoDetalhe:
    # POST ordens_servico/{os_id}/itens, json=item.model_dump(mode="json", exclude_none=True)

def remover_item_ordem_servico(self, os_id: int, item_id: int) -> OrdemServicoDetalhe:
    # request("DELETE", f"ordens_servico/{os_id}/itens/{item_id}", response_model=OrdemServicoDetalhe)
```

O seletor de peças reutiliza `list_produtos()`, que chama `GET produtos` (`ALL`) e devolve `estoque_qtd`, `preco_venda` e `ativo`. Não é necessário um endpoint novo.

## Reflex

### Estado — `workshop_state.py`

**Funções puras** (testadas isoladamente):

| Função | Papel |
| --- | --- |
| `can_edit_items(status, role)` | `can_operate_os(role)` e status em `ABERTA`/`EM_ANDAMENTO` |
| `produto_row(produto)` | `{id, label, codigo, nome, saldo, preco, preco_valor, disponivel}` para produtos ativos |
| `filtrar_produtos(rows, busca, limite=8)` | busca sem acento e sem diferenciar maiúsculas por código ou nome; limite de 8 resultados |
| `preview_item_total(tipo, produto, quantidade, valor)` | `Decimal \| None` do item em edição, para a prévia |
| `build_item_payload(tipo, produto_id, catalogo, quantidade, descricao, valor)` | monta o `ItemOSCreate`; lança `WorkshopFormError` para campos vazios, números inválidos e `quantidade > saldo` ("Saldo insuficiente: disponível X.") |
| `totais_row(detalhe)` | `{pecas, servicos, total}` formatados com `format_currency` |
| `item_row(item)` (alterada) | inclui `id`, `tipo` (rótulo), `descricao` (código · nome ou descrição do serviço), `unitario`, `total` e `baixado` |

**Variáveis novas:**

- detalhe: `detalhe_totais`;
- catálogo: `catalogo_produtos` e `catalogo_error`;
- formulário: `item_tipo` (`"PECA"`), `produto_busca`, `item_produto_id`, `item_quantidade` (`"1"`), `item_descricao`, `item_valor_unitario` e `item_error`;
- operações: `is_saving_item`, `item_to_remove` e `is_removing_item`.

**Variáveis computadas:**

- `can_edit_items`;
- `produtos_filtrados`;
- `produto_selecionado`;
- `item_preview`, a prévia formatada;
- `total_previsto`, que é o total da OS mais a prévia;
- `is_busy`, estendido para cobrir as operações de itens.

**Eventos:**

- `load_catalogo`, disparado ao abrir o painel;
- `set_item_tipo`, `set_produto_busca`, `select_produto`, `set_item_quantidade`, `set_item_descricao` e `set_item_valor_unitario`;
- `save_item`;
- `ask_remove_item`, `cancel_remove_item` e `confirm_remove_item`.

**Comportamento dos eventos:**

- Todos usam a proteção contra reentrada (`operation_is_blocked`) que já existe.
- **Sucesso:**
  - aplica o detalhe devolvido com `_apply_detail`, preservando o histórico da moto;
  - atualiza a linha da OS na lista, para o total;
  - limpa o formulário;
  - recarrega o catálogo;
  - mostra um toast de sucesso.
- **`XanoValidationError`:**
  - toast com `error_feedback`;
  - recarrega o catálogo e o detalhe, o que mostra o saldo e o status reais;
  - mantém o formulário para correção.
- **Outros erros:** `_xano_error_response`, como no restante da página, com a sessão tratada em `401`.

> **Implementado de outra forma:** não há evento `load_catalogo`. O catálogo é carregado dentro de `open_detail` quando a OS é editável pelo perfil, porque o formulário fica sempre visível nesse caso, e é recarregado depois de cada mutação ou rejeição. Os bloqueios de reentrada ficaram em `_operation_blocked()`, e `parse_decimal` foi movido para `formatting.py`.

### Componentes — `workshop_pages.py`

- **`itens_section`:**
  - tabela com as colunas Tipo, Item, Qtd, Unitário, Total e ação;
  - o botão remover aparece só com `can_edit_items`, e a remoção abre uma confirmação inline. Para peça baixada, o texto é "A peça volta ao estoque."
- **`custos_resumo`:** três valores, Peças + Mão de obra = Total OS, e a prévia "Total após inclusão" quando há item em edição.
- **`item_form`:** alternância Peça | Serviço.
  - **Peça:** campo de busca e lista de até 8 produtos com código, nome, saldo e preço. Os produtos sem saldo aparecem desabilitados com "sem saldo". Depois de escolher o produto, vêm a quantidade (com o saldo máximo indicado) e a prévia.
  - **Serviço:** descrição, quantidade e valor unitário.
  - Botão "Adicionar".
  - O componente de alternância (`rx.segmented_control` ou `rx.radio_group`) e a lista clicável são confirmados na skill `reflex-docs` durante o Apply.
- **Visibilidade:** `item_form` e as ações ficam dentro de `rx.cond(WorkshopState.can_edit_items, …)`. Para `VENDEDOR` e para OS encerrada, só a tabela e o resumo aparecem.
- **Lista de OS:** coluna "Total", vinda de `os_row`.

## Testes

| Arquivo | Cobertura |
| --- | --- |
| `tests/test_ordens_servico.py` | `ItemOSCreate`: regras por tipo, zeragem de campos, `gt 0`, casas decimais, `strip`; `ItemOrdemServico` legado (`tipo_item` nulo, sem `valor_unitario`); totais opcionais; cliente: caminho e corpo de `adicionar_item_ordem_servico` (`exclude_none`), `DELETE` de `remover_item_ordem_servico` com o detalhe devolvido, erro `400` virando `XanoValidationError` |
| `tests/test_workshop_state.py` | puras: `can_edit_items` por status e perfil, `filtrar_produtos` (acento, limite, inativos fora), `build_item_payload` (saldo excedido, número inválido, serviço sem valor), `preview_item_total`, `totais_row`, `item_row` legado; eventos: `save_item` com sucesso aplica o detalhe e limpa o formulário, `save_item` com erro de saldo mantém o formulário e recarrega o catálogo, `confirm_remove_item`, bloqueio por reentrada e por OS encerrada |
| `tests/test_ordens_servico_contracts.py` | inclusão e remoção com `enforce_role` `MECANICO`, sem `dblink`, trava da OS (`atualizado_em`) antes da releitura do status, `movimentar_estoque` dentro da transação, preço vindo de `preco_venda`, `try_catch`; cancelamento chamando `ESTORNO_OS` depois do `patch`; rotas legadas ainda `accessdenied` |
| `tests/test_estoque_contracts.py` | atualizado: a entrada usa `movimentar_estoque(ENTRADA)` dentro da transação e ordena por `id_produto`; `movimentar_estoque` grava o livro antes do produto e valida o saldo; índice único `(id_produto, versao_anterior)`; `PATCH produtos` descarta `versao_estoque` |
| `tests/test_integration_xano.py` | leitura: o `VENDEDOR` recebe `403` em inclusão e remoção; escrita (`XANO_TEST_ALLOW_WRITES`): baixa de peça, saldo insuficiente sem efeito, produto repetido, serviço sem estoque, totais, remoção com devolução, cancelamento devolvendo tudo, conclusão sem movimento, OS encerrada rejeitando itens; concorrência (opcional, `XANO_TEST_CONCURRENCY=true`): duas inclusões em threads disputando o último saldo |

Os testes que dependem do contrato antigo e passam a mudar: `test_estoque_contracts` (incremento via `db.edit produtos`), `test_ordens_servico_contracts` (texto da mensagem de bloqueio de itens, se afirmado) e `test_workshop_state` (`item_row`).

## Publicação

1. De preferência num branch do Xano: `xano workspace push -d ./xano --sync --dry-run -b <branch>` para revisar e, em seguida, sem `--dry-run`.
2. Executar a suíte de integração com credenciais por perfil e `XANO_TEST_ALLOW_WRITES=true` contra o branch.
3. Publicar no branch principal com `--sync`.

O `--sync` é necessário apenas para o relaxamento de `id_produto`. Os demais objetos são aditivos.

## Riscos e mitigação

| Risco | Mitigação |
| --- | --- |
| `function.run` dentro de `db.transaction` não participar da transação | Tarefa 0: validar a gramática e usar o teste de integração que já existe, `test_invalid_item_rolls_back_the_whole_receipt`. Quando a entrada passar a usar a função, ele prova que uma falha depois da movimentação desfaz o saldo. Plano B: repetir o corpo da função inline nos três endpoints, aceitando a duplicação com justificativa registrada |
| Premissa da trava de linha (D7) não se confirmar | Teste concorrente opcional na integração. Se falhar, plano B: versão otimista na OS, um contador em `ordens_servico` com índice único numa tabela de eventos de itens, espelhando a D6 |
| `--sync` remover algo criado só no workspace | Publicar a partir de um repositório sincronizado e revisar o `--dry-run` antes |
| Produto legado com `estoque_qtd` nulo | A função trata como `0`, então a baixa é rejeitada por saldo |
| Itens legados sem baixa devolverem estoque indevidamente | A devolução exige `estoque_baixado == true` (D10) |
| Mensagem genérica mascarar o motivo real numa corrida | Aceitável porque é raro; o Reflex recarrega catálogo e detalhe depois do erro, mostrando o estado real |
| Serviço com valor digitado errado | Visível no resumo antes de confirmar; remoção livre enquanto a OS estiver aberta |
| Deadlock entre entrada e cancelamento com vários produtos | Iteração por `id_produto` crescente nos dois fluxos; se ainda ocorrer, o banco aborta uma das transações, que é desfeita |
