# Design: entrada de mercadoria, estoque atômico e ajustes de consistência

## Visão geral

```text
Reflex (/estoque/entradas)
  EntradasState ──► XanoClient.registrar_entrada(EntradaMercadoriaCreate)
                        │  POST entrada_mercadoria  (JWT)
                        ▼
Xano  enforce_role(GERENTE) → resolve funcionário → db.transaction {
        valida fornecedor → valida itens → add cabeçalho → add itens
        → incrementa produtos.estoque_qtd → grava valor_total
      } → responde EntradaMercadoriaDetalhe
```

A regra de negócio fica inteiramente no Xano. O Reflex valida antes do envio para dar feedback rápido, mas não calcula nada que seja persistido.

## Modelo de dados (Xano)

### `entrada_mercadoria`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | int | PK |
| `id_fornecedor` | int → `fornecedores` | obrigatório no endpoint; fornecedor ativo |
| `numero_documento` | text `trim` | **novo**; obrigatório no endpoint |
| `id_funcionario` | int → `funcionarios` | **novo**; preenchido somente pelo stack |
| `data_entrada` | timestamp | `now`, definido pelo servidor (D5) |
| `valor_total` | decimal `min:0.01` | calculado pelo servidor |

Índices novos: `btree|unique (id_fornecedor, numero_documento)` e `btree (id_funcionario)`.

`numero_documento` e `id_funcionario` ficam opcionais no schema da tabela para não invalidar registros legados já existentes. A obrigatoriedade é garantida no input do endpoint e no stack.

### `itens_compra_estoque`

Sem alteração de schema. `quantidade min:1` e `valor_unitario min:0.01` já existem. `valor_total_item` não é persistido; é calculado na resposta do detalhe.

### `produtos`

Sem alteração de schema. `estoque_qtd min:0` continua sendo a proteção final.

## Contratos HTTP

### `POST entrada_mercadoria` — `GERENTE`

Requisição:

```json
{
  "id_fornecedor": 3,
  "numero_documento": "NF-000123",
  "itens": [
    {"id_produto": 10, "quantidade": 5, "valor_unitario": "42.90"},
    {"id_produto": 11, "quantidade": 2, "valor_unitario": "310.00"}
  ]
}
```

Campos como `id_funcionario`, `valor_total` e `data_entrada` são ignorados se enviados. O input do endpoint deixa de usar `dblink` aberto e declara apenas os campos acima.

Resposta `200`: `EntradaMercadoriaDetalhe` (ver abaixo).

Rejeições (todas sem efeito colateral):

| Situação | `error_type` Xano | HTTP |
| --- | --- | --- |
| Sem token ou token inválido | — | 401 |
| Perfil sem permissão / usuário sem funcionário | `accessdenied` | 403 |
| Fornecedor inexistente ou inativo | `inputerror` | 400 |
| `numero_documento` vazio | `inputerror` | 400 |
| Lista de itens vazia | `inputerror` | 400 |
| Produto repetido na mesma entrada | `inputerror` | 400 |
| Produto inexistente ou inativo | `inputerror` | 400 |
| `quantidade < 1` ou `valor_unitario < 0.01` | `inputerror` | 400 |
| Documento já registrado para o fornecedor | `inputerror` (pré-checagem) ou violação de índice único | 400 |

As mensagens das `precondition` novas serão escritas em português, pois serão exibidas ao usuário (ex.: "Fornecedor inativo ou inexistente.", "O produto PX100 está inativo.").

### `GET entrada_mercadoria` — `ALL`

Lista de `EntradaMercadoriaResumo`, ordenada por `data_entrada` decrescente:

```json
[{
  "id": 7, "numero_documento": "NF-000123", "data_entrada": 1790000000000,
  "valor_total": "834.50", "id_fornecedor": 3, "nome_fornecedor": "Moto Parts Ltda",
  "id_funcionario": 1, "nome_funcionario": "Ana Gerente", "quantidade_itens": 2
}]
```

### `GET entrada_mercadoria/{id}` — `ALL`

`EntradaMercadoriaDetalhe` = resumo + `itens`:

```json
{"itens": [{"id": 20, "id_produto": 10, "codigo": "PX100", "nome_produto": "Pastilha",
            "quantidade": 5, "valor_unitario": "42.90", "valor_total_item": "214.50"}]}
```

O enriquecimento (nomes de fornecedor, funcionário e produto) é feito no Xano, pois vendedor e mecânico não devem depender de `GET fornecedores` (D7).

### Endpoints bloqueados (D2)

`PUT`, `PATCH` e `DELETE entrada_mercadoria/{id}`, e `POST`, `PUT`, `PATCH` e `DELETE itens_compra_estoque[/{id}]` mantêm o arquivo no export, mas passam a executar apenas `enforce_role` seguido de rejeição explícita (`precondition (false)` com `error_type = "accessdenied"` e mensagem "Entradas de mercadoria são imutáveis."). Isso evita que um endpoint antigo, ainda publicado no workspace, contorne a regra de estoque.

`GET itens_compra_estoque` e `GET itens_compra_estoque/{id}` passam para `ALL`.

### Produtos (D3)

`PATCH` e `PUT produtos/{id}` descartam `estoque_qtd` do conjunto de campos gravados (no `PATCH`, removendo a chave antes do `db.patch`; no `PUT`, não mapeando o campo). `POST produtos` mantém o saldo inicial.

## Fluxo transacional no Xano

Esboço em pseudo-XanoScript; a sintaxe exata de `db.transaction`, iteração e agregação deve ser confirmada na documentação Xano durante o Apply.

```text
function.run "Quick Start/enforce_role" {user_id: $auth.id, required_role: "GERENTE"}
db.get user (id = $auth.id) → $auth_user
precondition ($auth_user.id_funcionario != null)          // accessdenied

db.transaction {
  db.get fornecedores (id = $input.id_fornecedor) → $fornecedor
  precondition ($fornecedor != null && $fornecedor.ativo)
  precondition ($input.numero_documento|trim != "")
  precondition (($input.itens|count) > 0)
  precondition (ids de produto sem repetição)
  db.query entrada_mercadoria (id_fornecedor, numero_documento) → precondition vazio

  db.add entrada_mercadoria {id_fornecedor, numero_documento,
                             id_funcionario: $auth_user.id_funcionario,
                             data_entrada: now, valor_total: 0.01 provisório} → $entrada
  var $total = 0
  foreach ($input.itens as $item) {
    precondition ($item.quantidade >= 1 && $item.valor_unitario >= 0.01)
    db.get produtos (id = $item.id_produto) → $produto
    precondition ($produto != null && $produto.ativo)
    db.add itens_compra_estoque {id_entrada: $entrada.id, ...$item}
    db.patch produtos (id) {estoque_qtd: $produto.estoque_qtd + $item.quantidade}
    $total = $total + $item.quantidade * $item.valor_unitario
  }
  db.patch entrada_mercadoria ($entrada.id) {valor_total: $total}
}
response = detalhe montado a partir de $entrada e dos itens gravados
```

Pontos de design:

- Todas as validações que dependem de leitura ficam **dentro** da transação para que o rollback cubra tudo.
- `valor_total` é gravado com um valor provisório positivo porque o schema exige `min:0.01`; alternativamente, validar os itens antes do `db.add` do cabeçalho e calcular o total primeiro, gravando o cabeçalho já com o valor final. O Apply deve preferir a segunda forma se a sintaxe permitir (duas passagens sobre `itens`: validar e calcular, depois gravar).
- Concorrência (D4): o incremento é leitura e escrita. O risco de atualização perdida em entradas simultâneas do mesmo produto é aceito e documentado; se o workspace permitir `db.direct_query`, o Apply pode substituir o `db.patch` por `UPDATE ... SET estoque_qtd = estoque_qtd + :qtd`.

## Cliente Python

### DTOs — `Projeto_HarleyStore/services/entradas.py`

```python
class ItemEntradaCreate(BaseModel):
    id_produto: int = Field(gt=0)
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)

class EntradaMercadoriaCreate(BaseModel):
    id_fornecedor: int = Field(gt=0)
    numero_documento: str = Field(min_length=1)       # com strip
    itens: list[ItemEntradaCreate] = Field(min_length=1)
    # model_validator: rejeita id_produto repetido

class EntradaMercadoriaResumo(BaseModel):              # extra="ignore"
    id: int
    numero_documento: str | None = None                # registros legados
    data_entrada: datetime | None = None
    valor_total: Decimal
    id_fornecedor: int
    nome_fornecedor: str | None = None
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    quantidade_itens: int = 0

class ItemEntrada(BaseModel): id, id_produto, codigo, nome_produto, quantidade, valor_unitario, valor_total_item
class EntradaMercadoriaDetalhe(EntradaMercadoriaResumo): itens: list[ItemEntrada] = []
```

`data_entrada` aceita o timestamp em milissegundos retornado pelo Xano; o DTO converte para `datetime`.

`ProdutoUpdate` perde `estoque_qtd` (D3).

### `XanoClient`

```python
def list_entradas(self) -> list[EntradaMercadoriaResumo]
def get_entrada(self, entrada_id: int) -> EntradaMercadoriaDetalhe
def registrar_entrada(self, entrada: EntradaMercadoriaCreate) -> EntradaMercadoriaDetalhe
```

Reutilizam `_list_resource` e `post(..., response_model=...)`. `registrar_entrada` serializa com `model_dump(mode="json")`, garantindo que `Decimal` vá como string numérica e que nenhum campo de autoria ou total seja enviado.

### Mapeamento de erros

- `400` passa a gerar `XanoValidationError`, como o `422`.
- Para `400`/`422`, a mensagem da exceção usa o campo `message` do corpo JSON quando ele for texto com até 200 caracteres; caso contrário, mantém a mensagem genérica atual. Nenhum outro campo do corpo é propagado.
- `401`, `403`, demais status e falhas de transporte mantêm o comportamento atual.

## Reflex

### Arquivos e responsabilidades

| Arquivo | Papel |
| --- | --- |
| `Projeto_HarleyStore/listing.py` (novo) | Funções puras `filter_rows`, `paginate`, `page_count`, `option_label` e `option_id`, compartilhadas por cadastros e entradas |
| `Projeto_HarleyStore/entradas_state.py` (novo) | `EntradasState(AuthState)` |
| `Projeto_HarleyStore/entradas_pages.py` (novo) | Página, tabela, modal de detalhe e formulário mestre-detalhe |
| `Projeto_HarleyStore/auth.py` | Matriz `ROUTE_ROLES`, `role_allows_route`, var `allowed_routes`, correção do toast vazio em `load_user` |
| `Projeto_HarleyStore/components.py` | Guard `guarded_page(content, route)`, `access_denied_page` movida para cá, links da sidebar |
| `Projeto_HarleyStore/cadastros_state.py` | Usa `listing.py`; `load_*` ignoram execução sem sessão; `list_error` visível |
| `Projeto_HarleyStore/cadastros_pages.py` | Guard por rota, callout de erro de lista, `estoque_qtd` somente na criação |
| `Projeto_HarleyStore/Projeto_HarleyStore.py` | Rota `/estoque/entradas`; `on_load` encadeando `restore_session` e carga; `protected_page` passa a usar o guard |

### Guard e matriz de rotas

```python
ROUTE_ROLES = {
    "/admin": {"GERENTE"},
    "/workshop": {"GERENTE", "MECANICO"},
    "/cadastros/clientes": ALL_ROLES,
    "/cadastros/motos-clientes": ALL_ROLES,
    "/cadastros/produtos": ALL_ROLES,
    "/cadastros/fornecedores": {"GERENTE"},
    "/cadastros/funcionarios": {"GERENTE"},
    "/estoque/entradas": ALL_ROLES,
}
```

- `role_allows_route` passa a ler `ROUTE_ROLES`; rota não mapeada é negada.
- `AuthState.allowed_routes` (computed var) devolve as rotas permitidas para o cargo atual.
- `guarded_page(content, route)`: sem sessão → `login_page()`; com sessão e rota permitida → `app_shell(content)`; caso contrário → `app_shell(access_denied_page())`. Mesmo comportamento já adotado em `/admin` e `/workshop`.
- A sidebar usa `allowed_routes.contains(rota)` em vez de predicados soltos, corrigindo "Produtos e peças" para o vendedor.
- `on_load=[AuthState.restore_session, <State>.load_x]`: a restauração ocorre antes da carga. Os eventos `load_*` retornam sem chamar o Xano quando `is_authenticated` é falso.
- `AuthState.load_user` só emite toast quando houver `error_message`, evitando toast vazio a cada restauração, o que ficaria visível agora que todas as rotas protegidas restauram a sessão.

### `EntradasState`

Estado:

- lista: `entradas: list[dict[str, str]]`, `search_text`, `current_page`, `page_size`, `list_error`;
- detalhe: `detail_open`, `detalhe: dict[str, str]`, `detalhe_itens: list[dict[str, str]]`;
- formulário: `form_open`, `fornecedor`, `numero_documento`, `itens_form: list[dict[str, str]]` (chaves `produto`, `quantidade`, `valor_unitario`), `form_error`;
- opções: `fornecedor_options`, `produto_options` (somente ativos, formato `"id - nome"`), carregadas ao abrir o formulário;
- flags: `is_loading_list`, `is_loading_detail`, `is_saving`.

Computed vars: `visible_rows`, `total_pages`, `can_register` (`employee_role == "GERENTE"`), `total_previsto` (texto formatado; só exibição), `is_busy`.

Eventos: `load_entradas`, `open_detail(id)`, `close_detail`, `open_create`, `close_form`, `set_fornecedor`, `set_numero_documento`, `add_item`, `remove_item(index)`, `set_item_field(index, field, value)`, `save_entrada`.

Regras:

- `open_create` e `save_entrada` verificam `can_register` antes de qualquer chamada.
- `save_entrada` monta `EntradaMercadoriaCreate` a partir do formulário; `ValidationError`/`ValueError`/`InvalidOperation` → `form_error` local sem chamar o Xano.
- Reentrada bloqueada por `operation_is_blocked`, reaproveitado de `cadastros_state.py`; flags limpas em `finally`.
- Sucesso: fecha o formulário, recarrega histórico e toast "Entrada registrada. Estoque atualizado.".
- `XanoValidationError` mantém o formulário aberto com a mensagem de negócio; `XanoPermissionError` mostra acesso negado; `XanoAuthenticationError` limpa a sessão.
- O formulário começa com um item vazio; `remove_item` não remove o último item.

### Interface

- Cabeçalho com título "Entradas de mercadoria" e botão "Nova entrada" (somente gerente).
- Tabela: data, documento, fornecedor, responsável, nº de itens, total e botão "Detalhes".
- Modal de detalhe: dados do cabeçalho e tabela de itens (código, produto, quantidade, preço de custo, subtotal).
- Formulário: select de fornecedor, input de documento, linhas de item com select de produto, quantidade, preço de custo e botão remover; botão "Adicionar item"; rodapé com total previsto e "Registrar entrada" desabilitado enquanto `is_busy`.
- Tema: `COLORS`, `PANEL` e `PRIMARY_BUTTON` de `styles/theme.py`, seguindo o padrão visual dos cadastros.
- IDs técnicos não aparecem como informação principal.

## Cenários de aceite

### Registro bem-sucedido

- **DADO** um gerente autenticado, um fornecedor ativo e os produtos ativos P1 (estoque 3) e P2 (estoque 0)
- **QUANDO** registrar a entrada "NF-1" com P1 × 5 a 10,00 e P2 × 2 a 25,50
- **ENTÃO** P1 DEVE ficar com estoque 8 e P2 com estoque 2
- **E** `valor_total` DEVE ser 101,00
- **E** `id_funcionario` DEVE ser o funcionário vinculado ao gerente

### Item inválido provoca rollback

- **DADO** uma entrada com P1 × 5 válido e P2 inativo
- **QUANDO** o endpoint processar a entrada
- **ENTÃO** a resposta DEVE ser `400`
- **E** nenhum cabeçalho, item ou alteração de estoque DEVE ser persistido

### Valores não positivos

- **DADO** um item com `quantidade = 0` ou `valor_unitario = 0` ou negativo
- **QUANDO** o formulário for enviado
- **ENTÃO** o DTO DEVE rejeitar o envio localmente
- **E** o Xano DEVE rejeitar o mesmo payload se enviado diretamente

### Fornecedor inativo

- **DADO** um fornecedor com `ativo = false`
- **QUANDO** uma entrada for enviada para ele
- **ENTÃO** a resposta DEVE ser `400` com mensagem legível e sem efeitos colaterais

### Documento duplicado

- **DADO** uma entrada já registrada com `(fornecedor 3, "NF-1")`
- **QUANDO** outra entrada com o mesmo par for enviada
- **ENTÃO** ela DEVE ser rejeitada e o estoque NÃO DEVE ser incrementado novamente

### Autoria adulterada

- **DADO** um payload com `id_funcionario` de outro funcionário e `valor_total = 1`
- **QUANDO** a entrada for registrada
- **ENTÃO** o registro DEVE conter o funcionário autenticado e o total calculado

### Perfis sem permissão de registro

- **DADO** um vendedor ou mecânico autenticado
- **QUANDO** acessar `/estoque/entradas`
- **ENTÃO** DEVE ver o histórico e o detalhe, sem o botão "Nova entrada"
- **E** um `POST entrada_mercadoria` forjado DEVE receber `403`

### Imutabilidade

- **DADO** uma entrada registrada
- **QUANDO** `PATCH entrada_mercadoria/{id}`, `DELETE entrada_mercadoria/{id}` ou `POST itens_compra_estoque` for chamado
- **ENTÃO** a operação DEVE ser rejeitada sem alterar dados

### Saldo protegido

- **DADO** um produto com estoque 8
- **QUANDO** um gerente enviar `PATCH produtos/{id}` com `estoque_qtd = 100`
- **ENTÃO** o estoque DEVE permanecer 8

### Sessão e rotas

- **DADO** um vendedor autenticado em `/cadastros/clientes`
- **QUANDO** recarregar a página (F5)
- **ENTÃO** a sessão DEVE ser restaurada e os botões de escrita DEVEM reaparecer
- **DADO** um vendedor autenticado
- **QUANDO** acessar diretamente `/cadastros/funcionarios`
- **ENTÃO** DEVE ver acesso negado dentro do App Shell
- **DADO** um navegador sem cookie de sessão
- **QUANDO** acessar `/estoque/entradas`
- **ENTÃO** DEVE ver a tela de login e nenhuma chamada autenticada DEVE ser feita

## Verificação

- `python -m unittest discover -s tests -v` (suíte existente + novos testes).
- `python -m py_compile` nos arquivos Python alterados.
- `reflex compile --dry`.
- Validação sintática dos XanoScript alterados.
- Com `XANO_API_BASE_URL` e perfis de teste disponíveis: roteiro manual dos cenários acima, incluindo o rollback. Sem o ambiente, registrar a limitação no Archive, como nas Changes anteriores.

## Riscos

| Risco | Mitigação |
| --- | --- |
| Sintaxe ou semântica de rollback de `db.transaction` diferente do esperado | Confirmar na documentação Xano antes de escrever o endpoint; teste manual de rollback em instância real |
| Atualização perdida em entradas simultâneas (D4) | Risco aceito e documentado; alternativa com `db.direct_query` |
| Endpoints antigos ainda publicados no workspace | Bloqueio explícito em vez de remoção do export (D2) |
| Registros legados sem documento/responsável | Campos opcionais na tabela e DTO de leitura tolerante |
| Mudança de comportamento na edição de produto (D3) | Decisão explícita na proposta; documentação e teste dedicados |
