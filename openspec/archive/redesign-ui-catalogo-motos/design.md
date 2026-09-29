# Design: design system Harley-Davidson e catálogo e reservas de motos

## Visão geral

```text
Fase A — design system (sem backend)
  styles/theme.py ── tokens (cores, tipografia, espaços, status) + contraste WCAG testado
  assets/harley.css ─ acento Radix #FF6600, títulos em caixa alta, foco, fundo
  ui_helpers.py ──── page_header, card, botões, status_badge, data_table, empty_state…
  components.py ──── shell (sidebar em seções, item ativo, recolhível), login, modal com blur, public_shell
  telas ──────────── login, dashboard, cadastros, entradas, oficina (lista + detalhe)

Fase B — catálogo
  /catalogo (público) ─ CatalogoState ─ cache 60 s ─ XanoClient.list_catalogo ─► GET catalogo (sem auth)
                                                   └ get_modelo_catalogo ───────► GET catalogo/{id}
  gerente ─ VendasState (aba Estoque) ─ criar/atualizar_modelo_moto ─► POST/PATCH modelos_moto (GERENTE)

Fase C — estoque e reservas
  /vendas ─ VendasState ─ list_motos_estoque ─────► GET motos (VENDEDOR, enriquecido)
                        ├ reservar_moto ──────────► POST motos/{id}/reserva ─┐
                        ├ cancelar_reserva_moto ──► POST motos/{id}/reserva/cancelar ─┤
                        │                             Vendas/transicionar_moto: versão + histórico (índice único)
                        └ cadastrar/atualizar_moto_estoque ─► POST/PATCH motos (GERENTE)
```

As regras de negócio continuam no Xano. O Reflex valida antes de enviar só para dar retorno imediato.

## Fase A — design system

### Tokens (`styles/theme.py`)

As chaves atuais de `COLORS` são mantidas e remapeadas, para que as telas existentes herdem a nova paleta sem troca de nomes. As chaves novas completam o sistema.

| Token | Valor | Uso |
| --- | --- | --- |
| `black` | `#000000` | fundo da aplicação (asfalto) |
| `graphite` | `#121212` | sidebar, barra superior, fundo de seções (preto fosco) |
| `surface` | `#1A1A1A` | cards, tabelas, modais (cinza industrial) |
| `surface_alt` | `#232323` | linha alternada, hover de linha |
| `border` | `#2E2E2E` | bordas padrão |
| `metal_edge` | `#3A3A3A` | borda dos botões metálicos |
| `orange` | `#FF6600` | acento, botão primário, foco, item ativo |
| `orange_hover` | `#FF7A1F` | hover do primário e da borda metálica |
| `orange_active` | `#E65C00` | clique do primário |
| `text` | `#FFFFFF` | texto principal |
| `muted` | `#A0A0A0` | texto secundário (cinza metálico) |
| `on_orange` | `#000000` | texto sobre laranja (D10) |
| `danger` | `#F87171` | erros e ações destrutivas |
| `overlay` | `rgba(0, 0, 0, 0.72)` | fundo do modal (com blur) |

- **`STATUS_COLORS`:** um só mapa `status → (fundo, texto, rótulo)` para OS (`ABERTA` laranja, `EM_ANDAMENTO` azul, `CONCLUIDA` verde, `CANCELADA` cinza) e motos (`DISPONIVEL` verde, `RESERVADA` âmbar, `VENDIDA` cinza). Todos os pares atingem 4,5:1.
- **Tipografia:**
  - `FONTS = {"heading": "'Oswald', 'Arial Narrow', sans-serif", "body": "'Inter', Arial, sans-serif"}`;
  - `HEADING_LETTER_SPACING = "0.06em"`.
- **Estilos:**
  - `PRIMARY_BUTTON`: laranja, texto `on_orange`, caixa alta;
  - `METAL_BUTTON`: gradiente `#2A2A2A → #141414`, borda `metal_edge`, hover com borda `orange_hover` e brilho;
  - `DANGER_BUTTON`, `CARD`, `TABLE` e `PANEL`, este mantido e remapeado;
  - `RADII` (4 e 8 px), `SHADOWS` (card e glow laranja) e `SPACING`, este mantido.
- **Contraste:** a função pura `contrast_ratio(fg, bg)` implementa a fórmula WCAG. O teste percorre os pares declarados em `TEXT_PAIRS` e exige ≥ 4,5:1.

| Par | Razão | Resultado |
| --- | --- | --- |
| `#FFFFFF` sobre `#1A1A1A` | 17,4:1 | AA/AAA |
| `#A0A0A0` sobre `#1A1A1A` | 6,66:1 | AA |
| `#A0A0A0` sobre `#000000` | 8,0:1 | AA |
| `#FF6600` sobre `#1A1A1A` (texto de acento) | 5,93:1 | AA |
| `#000000` sobre `#FF6600` (botão primário) | 7,15:1 | AA |
| `#FFFFFF` sobre `#FF6600` | 2,94:1 | **proibido** |

### Folha global (`assets/harley.css`)

```css
.radix-themes {                       /* acento da marca em todos os componentes Radix */
  --accent-9: #FF6600; --accent-10: #FF7A1F; --accent-contrast: #000000;
  --focus-8: #FF6600;
  --default-font-family: 'Inter', Arial, sans-serif;
  --heading-font-family: 'Oswald', 'Arial Narrow', sans-serif;
  --color-background: #000000;
}
.rt-Heading { text-transform: uppercase; letter-spacing: 0.06em; }
```

- `Projeto_HarleyStore.py` passa a criar `rx.App(stylesheets=[GOOGLE_FONTS_URL, "/harley.css"])`, com Oswald 500/700 e Inter 400/600, ambas sob licença OFL.
- Os nomes exatos das variáveis do Radix Themes da versão instalada são conferidos no Apply. Se `--accent-*` não bastar, a sobrescrita inclui a escala `--orange-*` do tema escuro.
- A caixa alta é feita por CSS: o conteúdo continua em caixa normal para leitores de tela e buscas.

### Componentes (`ui_helpers.py` e `components.py`)

| Componente | Assinatura | Observações |
| --- | --- | --- |
| `page_header` | `(title, subtitle="", *actions)` | título `rx.heading` (caixa alta), subtítulo `muted`, ações à direita |
| `section_title` | `(title)` | barra laranja de 3 px à esquerda |
| `card` | `(*children, **props)` | `surface`, borda, raio 8, sombra |
| `primary_button` / `metal_button` / `danger_button` | `(label, **props)` | aplicam os estilos dos tokens; `disabled` com opacidade |
| `status_badge` | `(status: Var, label: Var)` | `rx.match` sobre `STATUS_COLORS`; substitui o da oficina |
| `data_table` | `(headers: list[str \| tuple], body: Component, empty: str)` | cabeçalho em caixa alta, `muted`, linhas alternadas |
| `empty_state` | `(icon, message)` | usado por listas vazias |
| `stat_tile` | `(label, value)` | reservado ao resumo de custos da oficina e ao hero |
| `labeled`, `error_callout`, `operation_is_blocked` | atuais | sem mudança |
| `app_shell` | `(content)` | sidebar e barra superior; nome e perfil à direita; "Sair" metálico |
| `sidebar` | — | seções Operação / Oficina / Vendas / Cadastros; item ativo por `rx.State.router.page.path` (conferido no Apply); `rx.drawer` abaixo de 768 px |
| `public_shell` | `(content)` | barra superior com a assinatura "HARLEY STORE" e o link "Área do colaborador" (`/login`) |
| `login_page` | — | tela cheia preta com faixa laranja, assinatura textual, card com formulário |
| `modal_panel` | `(*children, width)` | fundo `overlay` com `backdrop_filter: blur(8px)`, borda superior laranja de 3 px, fecha com `Esc` |

### Aplicação nas telas

- **Login:** novo layout, mesmos eventos.
- **Dashboard:** `page_header("Visão geral")` e grade de cards de atalho para as rotas de `allowed_routes`, com ícone, nome e descrição curta. Sem métricas (D13).
- **Cadastros:** `page_header` + `data_table`; `preco_venda` exibido por `format_currency`; formulário em `modal_panel`.
- **Entradas:** `page_header` + `data_table`; modal e detalhe com o novo `card`.
- **Oficina:**
  - `workshop_pages.py` fica com a página, os filtros e a lista;
  - o detalhe da OS (transições, linha do tempo, itens, custos e histórico da moto) vai para `workshop_detail.py`;
  - `status_badge` e `custo` passam a vir de `ui_helpers.py`;
  - `workshop_state.py` não muda (D11).
- **Controle de regressão:** um teste percorre `Projeto_HarleyStore/**/*.py` e rejeita literais `#RRGGBB` e `rgba(` fora de `styles/theme.py`.

## Fase B — catálogo

### Tabela `modelos_moto` (nova)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | int | PK |
| `nome_modelo` | text `trim` | obrigatório; índice único |
| `familia` | enum `TOURING`, `CRUISER`, `ADVENTURE`, `SPORT` | obrigatório |
| `descricao` | text? `trim` | texto livre de vitrine |
| `preco_base` | decimal `min:0.01` | usado quando não há unidade disponível |
| `imagem_principal` | text `trim` | obrigatório; `https://` validado no endpoint |
| `variacoes_cor` | json | lista `[{nome, hex, imagem_url}]`, de 0 a 12 itens, validada no endpoint |
| `destaque` | bool? `=false` | candidato ao hero |
| `ativo` | bool? `=true` | soft delete; inativos saem do catálogo |
| `created_at` | timestamp `=now` | |

Índices: `unique (nome_modelo)`, `btree (familia)`.

### Contratos públicos (grupo `HARLEY`, sem `auth`)

`GET catalogo?familia=TOURING&busca=glide` devolve:

```json
[{
  "id": 3, "nome_modelo": "Street Glide", "familia": "TOURING",
  "descricao": "…", "imagem_principal": "https://…/street-glide.jpg",
  "variacoes_cor": [{"nome": "Vivid Black", "hex": "#0B0B0B", "imagem_url": "https://…/sg-black.jpg"}],
  "destaque": true, "preco_a_partir": 189900.00, "disponiveis": 2
}]
```

- Considera somente modelos com `ativo != false`, com o filtro `==?` para família, ordenados por `destaque desc, nome_modelo asc`.
- Busca: o operador `includes` existe no `where`, mas a documentação não informa se diferencia maiúsculas nem se há variante nula-segura. No Apply, confirmar no validador. A alternativa é aplicar a busca após a consulta, com `|to_lower` e `|contains` sobre a lista, que é pequena.
- `preco_a_partir` e `disponiveis` vêm de uma única consulta às unidades `DISPONIVEL`, agregada por `id_modelo` num `foreach`, sem N+1. Sem unidades disponíveis, `preco_a_partir = preco_base` e `disponiveis = 0`.
- A saída usa um `map` explícito com os campos acima. Nunca inclui unidades, chassi, cliente, vendedor nem `preco_base` separado.
- `GET catalogo/{modelo_id}` devolve o mesmo formato para um modelo ativo, ou `404`.
- Os dois endpoints entram numa lista explícita de rotas públicas no teste `test_only_login_endpoint_is_public`, que passa a chamar-se `test_public_surface_is_explicit`, e na spec emendada.

### Gestão (grupo `HARLEY`, `GERENTE`)

- `GET modelos_moto`: todos, inclusive inativos.
- `POST modelos_moto` e `PATCH modelos_moto/{id}`: inputs explícitos, sem `dblink`.
  - `imagem_principal` e cada `imagem_url` com `filters=trim|startsWith:https://`;
  - cada `hex` com `filters=pattern:^#[0-9A-Fa-f]{6}$`;
  - `variacoes_cor` como `object[]` com schema e `filters=max:12`, gravado em `json`;
  - `ativo` só no `PATCH`.
- Mensagens `400`: "Já existe um modelo com esse nome.", "A imagem deve ser uma URL https.", "Cor inválida: use o formato #RRGGBB.".

### DTOs (`services/catalogo.py`)

```python
FamiliaMoto = Literal["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
FAMILIA_LABELS = {"TOURING": "Touring", "CRUISER": "Cruiser", "ADVENTURE": "Adventure", "SPORT": "Sport"}

class VariacaoCor(BaseModel):          # str_strip_whitespace
    nome: str = Field(min_length=1, max_length=60)
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    imagem_url: str = Field(pattern=r"^https://\S+$")

class ModeloMotoCreate(BaseModel):
    nome_modelo: str = Field(min_length=1, max_length=120)
    familia: FamiliaMoto
    descricao: str | None = Field(default=None, max_length=2000)
    preco_base: Decimal = Field(gt=0, decimal_places=2)
    imagem_principal: str = Field(pattern=r"^https://\S+$")
    variacoes_cor: list[VariacaoCor] = Field(default_factory=list, max_length=12)
    destaque: bool = False

class ModeloMotoUpdate(BaseModel): ...    # todos opcionais + ativo
class ModeloMoto(ModeloMotoCreate):       # leitura interna: + id, ativo
class ModeloCatalogo(BaseModel):          # vitrine: id, nome_modelo, familia, descricao, imagem_principal,
                                          # variacoes_cor, destaque, preco_a_partir, disponiveis
```

### Cliente, `429` e cache

```python
def list_catalogo(self, *, familia: str | None = None, busca: str | None = None) -> list[ModeloCatalogo]
def get_modelo_catalogo(self, modelo_id: int) -> ModeloCatalogo
def list_modelos_moto(self) -> list[ModeloMoto]
def criar_modelo_moto(self, modelo: ModeloMotoCreate) -> ModeloMoto
def atualizar_modelo_moto(self, modelo_id: int, modelo: ModeloMotoUpdate) -> ModeloMoto
```

- Os métodos do catálogo usam `authenticated=False`.
- **`XanoRateLimitError(XanoError)`:** criado quando a resposta é `429`. `error_feedback` o traduz para "Muitas requisições ao Xano. Aguarde alguns segundos e tente novamente."
- **`CatalogoCache`** (em `services/catalogo.py`):
  - guarda a lista completa do catálogo no nível do módulo, com TTL de 60 s (`time.monotonic`);
  - `get(loader)` devolve a lista em cache ou chama o loader;
  - `invalidate()` é chamado depois de qualquer escrita de modelo ou unidade no mesmo processo;
  - com mais de um worker, cada processo tem o seu cache, o que é aceitável para uma vitrine.
- A tela carrega o catálogo inteiro uma vez e filtra família e busca localmente. Os filtros de servidor ficam disponíveis para outros consumidores.

### Reflex — `/catalogo`

- **`catalogo_state.py`:**
  - funções puras: `modelo_card(ModeloCatalogo) -> ModeloCard` (dataclass com `cores: list[CorCard]`), `filtrar_catalogo(cards, familia, busca)`, `preco_label` ("A partir de R$ 189.900,00"), `disponibilidade_label` ("2 disponíveis" / "Sob consulta") e `hero(cards)` (primeiro em destaque);
  - `CatalogoState(AuthState)` com `cards`, `familia`, `busca`, `imagem_por_modelo: dict[str, str]`, `detalhe` e `erro`;
  - eventos `load_catalogo` (usa o cache), `set_familia`, `set_busca`, `select_cor(modelo_id, imagem_url)`, `open_detail` e `close_detail`.
- **Composição de `catalogo_pages.py`:**
  - `public_shell`;
  - hero com a imagem do destaque em fundo, gradiente preto, tag "Lançamento", modelo e CTA;
  - `rx.tabs` por família e busca;
  - grade `rx.grid(columns=rx.breakpoints(initial="1", sm="2", lg="3"))`.
- **Card do modelo:**
  - imagem `imagem_por_modelo[id]` ou `imagem_principal`, em proporção 16:10 com `object_fit="cover"`;
  - família em `muted`, modelo em `rx.heading` (caixa alta), preço em laranja e badge de disponibilidade;
  - swatches como botões circulares com `aria_label` e `title` iguais ao nome da cor, com anel laranja no selecionado;
  - CTA "Tenho interesse": para o visitante, leva a `/login`; para vendedor e gerente, leva a `/vendas?modelo={id}`.
- **Detalhe:** `modal_panel` com imagem grande, swatches, descrição e disponibilidade.

> **Implementado de outra forma:**
> - O visitante vê "Fale com um vendedor", que abre o detalhe com a orientação de procurar a loja, em vez de ir para `/login`.
> - O perfil de venda é lido de `AuthState.allowed_routes`, e não de uma variável computada do `CatalogoState`.
> - O detalhe usa os cards em cache, sem chamar `GET catalogo/{id}`.
> - Um flag `carregado` evita que o estado vazio apareça antes do fim da primeira carga.
- **Mecânica conferida no Propose:** `rx.foreach` aninhado com linhas em dataclass e `rx.State.router.page.path` compilam no Reflex 0.9.12.

## Fase C — estoque e reservas

### Tabela `motos` (evolução)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `clientes_id` | int? → `clientes` | existente; cliente da reserva (e da venda, na Change 9) |
| `marca`, `modelo` | text? | existentes; legado, apenas leitura |
| `id_modelo` | int? → `modelos_moto` | **novo**; obrigatório no novo `POST` |
| `chassi` | text? `trim\|upper` | **novo**; índice único; 17 caracteres VIN (`^[A-HJ-NPR-Z0-9]{17}$`) no input |
| `cor` | text? `trim` | **novo**; nome de uma das `variacoes_cor` do modelo |
| `ano_modelo` | int? `min:1990` | **novo** |
| `preco_venda` | decimal? `min:0.01` | **novo** |
| `status` | enum? `DISPONIVEL`, `RESERVADA`, `VENDIDA` `=DISPONIVEL` | **novo**; muda só por `Vendas/transicionar_moto` |
| `id_vendedor_reserva` | int? → `funcionarios` | **novo**; do JWT |
| `reservada_ate` | timestamp? | **novo**; `now + dias_validade` |
| `versao_status` | int? `min:0` | **novo**; nulo equivale a 0 |
| `atualizado_em` | timestamp? | **novo** |

Todos os campos novos são anuláveis. Unidades legadas sem modelo ficam fora do catálogo e aparecem em `/vendas` como "Sem modelo". O push é aditivo, sem `--sync`.

### Tabela `historico_status_moto` (nova)

| Campo | Tipo |
| --- | --- |
| `id_moto` | int → `motos` |
| `status_anterior` | enum? (nulo no cadastro) |
| `status_novo` | enum |
| `versao_anterior` | int `min:0` |
| `id_funcionario` | int → `funcionarios` (JWT) |
| `id_cliente` | int? → `clientes` |
| `observacao` | text? `trim` |
| `created_at` | timestamp `=now` |

Índices:

- `unique (id_moto, versao_anterior)`: o comentário fica acima de `index = [`;
- `btree (id_moto)`;
- `btree (created_at desc)`.

### Função `Vendas/transicionar_moto`

Chamada dentro da transação de quem a invoca, no mesmo padrão de `Estoque/movimentar_estoque`.

```text
input: id_moto, status_esperado, status_novo, id_funcionario, id_cliente?, reservada_ate?, observacao?
db.get motos (id, status, versao_status, clientes_id, id_vendedor_reserva, reservada_ate) as $moto
precondition $moto != null                         → notfound "Moto não encontrada."
precondition ($moto.status ?? "DISPONIVEL") == status_esperado → "A moto foi alterada por outro usuário. Atualize e tente novamente."
$versao = $moto.versao_status ?? 0
db.add historico_status_moto {…, versao_anterior: $versao}   // índice único serializa
db.patch motos {status, clientes_id, id_vendedor_reserva, reservada_ate, versao_status: $versao + 1, atualizado_em: now}
```

- **Reserva:** grava cliente, vendedor e validade.
- **Cancelamento:** limpa os três campos (`null`).

### Endpoints de reserva (`VENDEDOR`, que inclui `GERENTE`)

**`POST motos/{id}/reserva`**

- Corpo: `{"id_cliente": 5, "dias_validade": 7, "observacao": "Sinal combinado"}`.
- Inputs: `dias_validade` com `filters=min:1|max:30`, `observacao` opcional com `max:500`.
- Pré-checagens (`400`, com mensagens específicas):
  - moto inexistente: `404`;
  - status diferente de `DISPONIVEL`: "Esta moto não está disponível para reserva.";
  - moto sem modelo: "Cadastre o modelo desta moto antes de reservá-la.";
  - cliente inativo ou inexistente: "Cliente inativo ou inexistente.".
- Execução: `try_catch { db.transaction { transicionar_moto(DISPONIVEL → RESERVADA, reservada_ate = now + dias) } }`. O `catch` responde `400` "A moto foi alterada por outro usuário. Atualize e tente novamente.".
- Resposta: `Vendas/detalhe_moto`, com a unidade, o modelo, o cliente, o vendedor e o histórico.

**`POST motos/{id}/reserva/cancelar`**

- Corpo: `{"motivo": "Cliente desistiu"}`, com o motivo obrigatório.
- Regras:
  - status `RESERVADA`;
  - o autor do cancelamento precisa ser o vendedor da reserva, um `GERENTE` ou qualquer vendedor quando `reservada_ate < now`;
  - fora disso, `403` "Somente quem reservou ou um gerente pode cancelar esta reserva antes do vencimento.".
- Execução: `transicionar_moto(RESERVADA → DISPONIVEL)`, gravando o motivo como observação.

### Leitura e gestão de unidades

- **`GET motos`** (`VENDEDOR`):
  - filtros `status` e `id_modelo`;
  - enriquecido com `nome_modelo`, `familia`, `nome_cliente`, `nome_vendedor` e `reserva_vencida`;
  - os nomes são resolvidos com uma consulta por tabela e `find`, como na lista de OS.
- **`GET motos/{id}`** (`VENDEDOR`): `Vendas/detalhe_moto`, com o histórico.
- **`POST motos`** (`GERENTE`):
  - inputs explícitos `id_modelo`, `chassi`, `cor`, `ano_modelo` e `preco_venda`;
  - valida modelo ativo, cor dentro das variações do modelo (se houver variações), chassi único em `motos` **e** em `motos_clientes`, e ano entre 1990 e o ano seguinte;
  - grava `status = DISPONIVEL` e o histórico `null → DISPONIVEL` na mesma transação.
- **`PATCH motos/{id}`** (`GERENTE`):
  - `cor`, `ano_modelo` e `preco_venda`;
  - `chassi` só enquanto `DISPONIVEL`;
  - `status`, `clientes_id`, `id_vendedor_reserva` e `reservada_ate` são descartados.
- **`PUT motos/{id}`:** bloqueado (`403`), no mesmo padrão dos demais.

### DTOs (`services/motos.py`, reescrito)

```python
StatusMoto = Literal["DISPONIVEL", "RESERVADA", "VENDIDA"]

class MotoEstoqueCreate(BaseModel):   # str_strip_whitespace; chassi → upper
    id_modelo: int = Field(gt=0)
    chassi: str = Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")
    cor: str = Field(min_length=1, max_length=60)
    ano_modelo: int = Field(ge=1990)          # validator: <= ano atual + 1
    preco_venda: Decimal = Field(gt=0, decimal_places=2)

class MotoEstoqueUpdate(BaseModel): ...     # cor, ano_modelo, preco_venda, chassi (opcionais)
class MotoEstoque(BaseModel): ...           # leitura enriquecida; status None → "DISPONIVEL"; campos legados opcionais
class HistoricoStatusMoto(BaseModel): ...
class MotoEstoqueDetalhe(MotoEstoque): historico: list[HistoricoStatusMoto] = []
class ReservaMotoCreate(BaseModel):
    id_cliente: int = Field(gt=0)
    dias_validade: int = Field(default=7, ge=1, le=30)
    observacao: str | None = Field(default=None, max_length=500)
class CancelamentoReservaMoto(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)
```

`Moto`, `MotoCreate`, `MotoUpdate`, `list_motos`, `create_moto` e `update_moto` são removidos. O teste genérico de `test_xano_client.py` que usa `Moto` passa a usar um modelo próprio do teste.

### Cliente

```python
def list_motos_estoque(self, *, status: str | None = None, id_modelo: int | None = None) -> list[MotoEstoque]
def get_moto_estoque(self, moto_id: int) -> MotoEstoqueDetalhe
def cadastrar_moto_estoque(self, moto: MotoEstoqueCreate) -> MotoEstoqueDetalhe
def atualizar_moto_estoque(self, moto_id: int, moto: MotoEstoqueUpdate) -> MotoEstoqueDetalhe
def reservar_moto(self, moto_id: int, reserva: ReservaMotoCreate) -> MotoEstoqueDetalhe
def cancelar_reserva_moto(self, moto_id: int, cancelamento: CancelamentoReservaMoto) -> MotoEstoqueDetalhe
```

### Reflex — `/vendas`

- **`vendas_state.py`:**
  - funções puras: `can_sell(role)`, `can_manage_catalog(role)`, `can_cancel_reservation(row, role, employee_id, agora)`, `moto_row`, `filtrar_motos(rows, aba, modelo, busca)`, `build_reserva_payload`, `build_modelo_payload` (com o editor de cores) e `build_moto_payload`;
  - `VendasState(AuthState)`: aba ativa, linhas, filtros (lê `?modelo=` na carga), modal de reserva (clientes ativos, dias, observação), cancelamento (motivo), detalhe com linha do tempo e, para o `GERENTE`, os formulários de modelo e de unidade;
  - reentrância protegida por `operation_is_blocked`;
  - toasts por `toast_error`/`toast_success`;
  - depois de uma rejeição, recarrega a unidade e a lista, como na oficina;
  - escritas de modelo ou unidade chamam `CatalogoCache.invalidate()`.
- **`vendas_pages.py`:**
  - `page_header("Vendas de motos")`;
  - abas Disponíveis | Reservadas | Vendidas | Estoque, esta só para `GERENTE`;
  - `data_table` com modelo, cor (swatch), chassi (últimos 6 caracteres), ano, preço, status, cliente e validade;
  - badge "Vencida" em reservas vencidas;
  - modais de reserva, cancelamento, detalhe, modelo e unidade;
  - no editor de cores, cada linha tem nome, `hex` (com swatch ao vivo) e URL da imagem, com adicionar e remover.
- **Rotas:** `ROUTE_ROLES["/vendas"] = {"GERENTE", "VENDEDOR"}`. `/catalogo` fica fora de `ROUTE_ROLES` (é pública) e aparece na sidebar para todos.

## Testes

| Arquivo | Cobertura |
| --- | --- |
| `tests/test_theme.py` (novo) | `contrast_ratio`; todos os `TEXT_PAIRS` e `STATUS_COLORS` com 4,5:1 ou mais; nenhum literal de cor fora de `styles/theme.py` e `assets/` |
| `tests/test_ui_helpers.py` | novos componentes constroem; `status_badge` cobre os 7 status; helpers definidos uma única vez |
| `tests/test_catalogo.py` (novo) | `VariacaoCor` (hex, https), `ModeloMotoCreate`, `ModeloCatalogo`; cliente: `list_catalogo` sem `Authorization`, filtros como query; `429` gerando `XanoRateLimitError`; `CatalogoCache` (TTL com relógio injetado, `invalidate`) |
| `tests/test_catalogo_state.py` (novo) | cards, rótulo de preço, disponibilidade, hero, filtro por família e busca sem acento, `select_cor` sem chamar o Xano, carga via cache |
| `tests/test_motos.py` (novo) | DTOs de unidade (VIN, ano, preço), reserva (dias de 1 a 30), cancelamento; métodos do cliente |
| `tests/test_vendas_state.py` (novo) | regras puras de permissão e cancelamento (vencida, própria, gerente), payloads, eventos de reserva (sucesso, conflito com recarga, reentrância), aba Estoque só para o gerente |
| `tests/test_catalogo_vendas_contracts.py` (novo) | endpoints públicos sem `auth` e com `map` sem campos internos; gestão com `GERENTE` e sem `dblink`; validação `https`/`hex`/VIN; `transicionar_moto` grava o histórico antes do `patch`; índice único; reserva com `try_catch`; `PUT` bloqueado; `POST`/`PATCH` sem `status` |
| `tests/test_security_contracts.py` | superfície pública explícita (`auth/login`, `GET catalogo`, `GET catalogo/{id}`) |
| `tests/test_authentication.py` | `/vendas` para `GERENTE`/`VENDEDOR`; `MECANICO` negado |
| `tests/test_integration_xano.py` | leitura: catálogo sem token e sem campos internos; escrita: cadastro de modelo e unidade, reserva, cancelamento por outro vendedor (`403`) e pelo gerente; concorrência (`XANO_TEST_CONCURRENCY`): duas reservas simultâneas |

A verificação visual segue a skill `reflex-process-management`: subir a aplicação e revisar Login, Dashboard, Cadastros, Entradas, Oficina, Catálogo e Vendas em 1440 px e 390 px, conferindo o foco pelo teclado nos swatches e nas abas.

## Publicação

Todas as alterações de schema são aditivas (tabelas novas e campos anuláveis), então basta `xano workspace push -d ./xano`. Recomenda-se publicar primeiro num branch e cadastrar ao menos um modelo por família com imagens próprias antes de abrir `/catalogo`.

## Riscos e mitigação

| Risco | Mitigação |
| --- | --- |
| Escopo grande (redesign global + dois módulos) | três fases com verificação própria; a Fase A não toca o backend e pode ser arquivada como marco interno |
| `429` numa página pública | cache de 60 s, filtros locais e erro tipado com mensagem de espera |
| Variáveis CSS do Radix mudarem entre versões | sobrescrita concentrada em `harley.css`; conferida no Apply e pela verificação visual |
| Endpoint público raspado | projeção fechada, só dados de vitrine; sem dados pessoais nem chassi |
| Imagens externas quebradas ou sem direitos | URL `https` validada; fallback para `imagem_principal` e depois para um placeholder em `assets/`; responsabilidade da loja registrada na proposta |
| Unidades legadas sem modelo | excluídas do catálogo; exibidas como "Sem modelo" em `/vendas`; reserva exige modelo |
| Chassi duplicado entre estoque e motos de clientes | checagem cruzada no `POST motos` |
| Regressão visual nas telas existentes | a lógica dos estados não muda (testes atuais seguem valendo); revisão visual por tela; teste de cores fixas |
| Fontes externas (Google Fonts) indisponíveis | pilhas de fallback (`Arial Narrow`, `Arial`); autohospedagem em `assets/fonts` como alternativa |
