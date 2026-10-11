# Design: venda de balcão de peças (Change 11)

> **Situação:** arquivada em 2026-10-11. Decisões D1 a D10 aprovadas e implementadas; publicada no Xano (commit `c29bfa5`, enum `SAIDA_VENDA` confirmado no remoto); specs e docs atualizados. Pendentes do usuário: integração real com credenciais e verificação visual autenticada.

## 1. Origem do escopo

| Fonte | O que diz |
| --- | --- |
| `openspec/archive/fechamento-financeiro-operacoes/design.md`, D1 | Venda no balcão vai para a Change 11, "que reutilizará o resumo"; exige itens de transação e um novo tipo de movimentação de estoque. |
| `docs/domain-model.md` → *Transacoes* | Transações não têm itens; o balcão (`BALCAO`/`PECAS`) "depende de uma decisão de modelagem". |
| `docs/project-overview.md` §3 e §9; relatório do projeto (PDF) | Unificar vendas no balcão, motos e serviços; priorizar a integridade do estoque "durante a baixa via OS ou Vendas no Balcão". |
| `docs/Lojas_HarleyDavidson.pdf` | Saídas de estoque por "vendas realizadas no balcão" ou por OS; vendedores fazem as vendas no balcão. Nenhum documento distingue `PECAS` de `BALCAO` (D1). |
| `docs/auditoria-arquitetura-changes-1-7.md`, débito 1 | A integração com escrita e concorrência ainda não rodou contra o Xano real. |

Padrões existentes que esta Change reutiliza:

| Padrão | Onde está |
| --- | --- |
| Validações com mensagem específica fora da transação; só gravações dentro; `catch` com mensagem de conflito | `entrada_mercadoria_POST.xs` |
| Itens processados em ordem de `id_produto` (evita deadlock) | `entrada_mercadoria_POST.xs`, cancelamento de OS |
| Preço fotografado de `produtos.preco_venda` e saldo checado antes da transação | `ordens_servico_id_itens_POST.xs` |
| Saldo e concorrência pelo livro (índice único `(id_produto, versao_anterior)`) | `Estoque/movimentar_estoque` |
| Autoria pelo JWT; `enforce_role "VENDEDOR"` (aceita `GERENTE` e `VENDEDOR`) | `vender_moto_POST.xs` |
| Busca de produtos com saldo e preço | `workshop_state.produto_row` e `filtrar_produtos` |
| Trava de reentrada e `yield` antes da chamada ao Xano | regra de `tests/test_loading_states.py` |

## 2. Visão geral

```text
/balcao (GERENTE, VENDEDOR) ─ BalcaoState ─ XanoClient.vender_balcao ─► POST balcao/vendas
                                                                         pré-validações (mensagens específicas)
                                                                         ├ chave já usada → recibo existente (D5)
                                                                         try_catch + db.transaction:
                                                                           relê preços (ordem de id_produto) e confere o total (D4)
                                                                           db.add transacoes (BALCAO)
                                                                           por item: db.add itens_transacao
                                                                                     Estoque/movimentar_estoque (SAIDA_VENDA, id_transacao)
                                                                         └ Balcao/detalhe_venda → recibo

/financeiro (GERENTE): Financeiro/resumo_operacoes já soma BALCAO como receita (sem mudança no Xano)
```

As regras ficam no Xano. O Reflex valida o carrinho só para dar retorno imediato.

## 3. Decisões

- **P0 — Pendência da Change 10 (pré-requisito):** a Change 10 foi arquivada sem aplicar seus deltas de spec. Não existe `openspec/specs/financeiro.md`, e `arquitetura-e-contratos.md` ainda chama a imutabilidade de "proposta". Os deltas foram aplicados antes desta Change, para que os deltas dela partam das specs corretas. *Concluída em 2026-10-09:* `openspec/specs/financeiro.md` criada e deltas aplicados em `arquitetura-e-contratos.md` e `oficina-ordens-servico.md`.
- **D1 — Tipo da transação:** toda venda no balcão é `BALCAO`, com ou sem cliente. `PECAS` fica sem uso automático, como `COMPRA` depois da Change 10, e continua contando como receita no resumo. *Aprovada:* nenhum documento distingue os dois tipos, e um único tipo mantém o resumo legível. A alternativa descartada é `PECAS` para cliente identificado e `BALCAO` para consumidor final, uma distinção que não vem do domínio.
- **D2 — Modelagem dos itens:** tabela nova `itens_transacao`, ligada a `transacoes` por `id_transacao`. A própria transação é o cabeçalho (tipo, funcionário, cliente, data, total). O nome é genérico para servir a futuros tipos com itens. *Aprovada.* A alternativa descartada é uma tabela de cabeçalho `vendas_balcao` com itens próprios e a transação apontando para ela, o que repete funcionário, cliente, data e total em dois lugares.
- **D3 — Preço:**
  - `valor_unitario` é a fotografia de `produtos.preco_venda`, lida pelo Xano dentro da transação;
  - o payload não traz preço nem total por item;
  - não há desconto nesta Change.

  *Aprovada* (mesmo padrão das peças na OS).
- **D4 — Total conferido:** o Reflex envia `total_esperado`, o total exibido ao vendedor. O Xano recalcula e, se divergir (um preço mudou desde o carregamento da tela), recusa com `400` e o novo total, sem gravar. Assim o cliente nunca paga um valor diferente do que viu. *Aprovada.* A alternativa descartada é aceitar o preço atual em silêncio e mostrar a diferença só no recibo.
- **D5 — Idempotência:**
  - o Reflex gera uma `chave_venda` (UUID v4) por carrinho, mantém a mesma em novas tentativas e só a renova depois de uma venda concluída ou de limpar o carrinho;
  - a chave é gravada em cada item, com índice único `(chave_venda, id_produto)`;
  - repetir uma chave já gravada devolve o recibo da venda existente (`200`), sem nova baixa nem receita.

  *Aprovada:* o `XanoClient` tem timeout de 10 s e não repete pedidos, então uma resposta perdida seguida de novo clique venderia duas vezes. O índice fica na tabela nova, sem linhas nulas, e evita o risco de nulos em índice único descrito no D8 da Change 10. A alternativa descartada é confiar só na trava do botão.
- **D6 — Baixa de estoque:**
  - novo tipo `SAIDA_VENDA` no livro e campo `id_transacao` em `movimentacoes_estoque`;
  - `Estoque/movimentar_estoque` subtrai em `SAIDA_OS` e `SAIDA_VENDA` e exige produto ativo nas duas saídas;
  - o saldo é verificado antes da transação, com a mensagem "Saldo insuficiente para …", e de novo dentro dela pelo livro;
  - uma corrida entre as duas leituras desfaz tudo e responde com a mensagem de conflito.

  *Aprovada.* A alternativa descartada é reutilizar `SAIDA_OS` com `id_os` nulo, o que mistura origens no kardex.
- **D7 — Cliente:** `id_cliente` opcional. Nulo significa consumidor final; informado, o cliente deve estar ativo. Sem moto do cliente nesta Change. *Aprovada.*
- **D8 — Acesso e consultas:**
  - `POST balcao/vendas` e `/balcao` para `GERENTE` e `VENDEDOR`;
  - `MECANICO` não, porque as peças dele saem pela OS;
  - não há endpoint de listagem ou detalhe nesta Change: o recibo vem na resposta do `POST`, e o gerente vê as vendas no `/financeiro` (dados financeiros seguem só do `GERENTE`, D6 da Change 10).

  *Aprovada.* A alternativa descartada é um `GET balcao/vendas/{id}` para reimprimir o recibo, que fica para quando houver impressão.
- **D9 — Limites:** de 1 a 30 itens por venda, cada produto uma única vez; o carrinho soma a quantidade quando o mesmo produto é adicionado de novo. *Aprovada:* cada item custa cerca de 5 operações de banco dentro da transação (leitura do preço, item, leitura, livro e produto), e o plano Free limita tempo e taxa. A alternativa descartada é sem limite, como a entrada de mercadoria.
- **D10 — Deploy:**
  - o push amplia o enum `movimentacoes_estoque.tipo` e o enum de entrada de `movimentar_estoque`;
  - segundo o histórico do projeto, um push parcial não relaxa restrições, e a ampliação de enum pode exigir `--sync`, sempre sem `--delete`;
  - decidir pelo `--dry-run`, com o OK duplo de mudança de banco.

  *Aprovada.*

## 4. Xano

### 4.1 Tabela nova `itens_transacao`

```xs
// Itens de uma transação comercial (Change 11). Hoje só a venda no balcão (BALCAO).
// Imutáveis: não há rotas genéricas; nascem em POST balcao/vendas.
table itens_transacao {
  auth = false

  schema {
    int id
    int id_transacao {
      table = "transacoes"
    }

    int id_produto {
      table = "produtos"
    }

    int quantidade filters=min:1
    // Fotografia de produtos.preco_venda no fechamento (D3).
    decimal valor_unitario filters=min:0.01
    decimal valor_total_item filters=min:0.01

    // UUID do carrinho gerado pelo Reflex (D5): repetir a chave devolve a venda já registrada.
    text chave_venda filters=trim
    timestamp created_at?=now
  }

  // (chave_venda, id_produto) único: um produto por venda e uma venda por chave.
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_transacao"}]}
    {type: "btree", field: [{name: "id_produto"}]}
    {
      type : "btree|unique"
      field: [{name: "chave_venda"}, {name: "id_produto"}]
    }
  ]
}
```

### 4.2 `movimentacoes_estoque` (alteração)

- `enum tipo`: acrescenta `SAIDA_VENDA`.
- Campo novo `int? id_transacao? {table = "transacoes"}` ("Origem SAIDA_VENDA"), com `btree`.
- Linhas existentes ficam com `id_transacao` nulo.

### 4.3 `Estoque/movimentar_estoque` (alteração)

- Entrada: o enum `tipo` ganha `SAIDA_VENDA`; novo `int? id_transacao?`, gravado no livro.
- Saldo: subtrai quando `tipo` é `SAIDA_OS` ou `SAIDA_VENDA`.
- Produto inativo: recusado em `SAIDA_OS` e `SAIDA_VENDA`. A devolução (`ESTORNO_OS`) a produto desativado continua permitida.
- `ENTRADA`, `SAIDA_OS` e `ESTORNO_OS` não mudam de comportamento.

### 4.4 `POST balcao/vendas` (novo)

- **Arquivo:** `xano/api/harley/balcao/vendas_POST.xs` (grupo `HARLEY`, `auth = "user"`).
- **Perfil:** `enforce_role "VENDEDOR"` (`GERENTE` e `VENDEDOR`); o usuário precisa estar vinculado a um funcionário.

**Entrada (JSON):**

| Campo | Tipo | Regra |
| --- | --- | --- |
| `chave_venda` | text | obrigatório, `trim`, até 64 caracteres (UUID do carrinho) |
| `id_cliente` | int? | opcional; se informado, cliente ativo |
| `total_esperado` | decimal | obrigatório, `>= 0.01`; comparado com 2 casas |
| `itens` | object[] | 1 a 30; `id_produto` (int `>= 1`, sem repetição) e `quantidade` (int `>= 1`) |

```json
{
  "chave_venda": "3f2c9a4e-7b1d-4c8e-9f0a-2d6b5e8c1a7f",
  "id_cliente": 14,
  "total_esperado": 389.70,
  "itens": [
    {"id_produto": 7, "quantidade": 2},
    {"id_produto": 12, "quantidade": 1}
  ]
}
```

**Algoritmo:**

1. **Pré-validações (fora da transação, mensagens específicas):**
   1. Perfil e funcionário vinculado.
   2. `chave_venda` não vazia.
   3. **Repetição (D5):** se existe um item com essa `chave_venda`, responde `Balcao/detalhe_venda` da transação dele e não grava nada.
   4. Itens: ao menos 1, no máximo 30, sem produto repetido.
   5. Cliente informado: existe e está ativo.
   6. Para cada item:
      - o produto existe e está ativo;
      - `(estoque_qtd ?? 0) >= quantidade`;
      - acumula `quantidade × preco_venda`.
   7. O total acumulado (`round:2`) deve ser igual a `total_esperado` (D4).
2. **Gravação (`try_catch` + `db.transaction`):**
   1. Percorre os itens em ordem de `id_produto`: relê `preco_venda` e `ativo` de cada produto e monta as linhas (`valor_unitario`, `valor_total_item = round(quantidade × preço, 2)`) e o total.
   2. Confere o total de novo. Uma divergência aqui é uma corrida e cai no `catch`.
   3. `db.add transacoes`:
      - `tipo_transacao = "BALCAO"`, `id_funcionario` do JWT, `id_cliente` ou nulo;
      - `id_moto_cliente` e `id_os` nulos;
      - `data_transacao = now`, `valor_total` = total.
   4. Para cada linha, na mesma ordem:
      - `db.add itens_transacao`, com `chave_venda`;
      - `Estoque/movimentar_estoque` com `SAIDA_VENDA`, `quantidade`, `id_funcionario` e `id_transacao`.
   5. `catch` → `400` "A venda não foi registrada: o estoque ou os preços mudaram durante o fechamento. Revise o carrinho e tente novamente."
3. **Resposta:** `Balcao/detalhe_venda` da transação criada.

**Concorrência:**

| Situação | Resultado |
| --- | --- |
| Duas vendas da última unidade | Ambas passam na pré-validação. O índice único `(id_produto, versao_anterior)` ou a verificação de saldo dentro de `movimentar_estoque` desfaz a segunda, que recebe a mensagem de conflito. |
| A mesma chave enviada duas vezes ao mesmo tempo | O índice único `(chave_venda, id_produto)` desfaz a segunda. A próxima tentativa encontra a venda pela etapa 1.3. |

**Saída (`200`):**

```json
{
  "id_transacao": 128,
  "tipo_transacao": "BALCAO",
  "data_transacao": 1791990000000,
  "valor_total": 389.70,
  "id_cliente": 14,
  "nome_cliente": "Ana Souza",
  "id_funcionario": 3,
  "nome_funcionario": "Carlos Vendedor",
  "itens": [
    {"id_produto": 7, "codigo": "FLT-0001", "nome_produto": "Filtro de óleo", "quantidade": 2, "valor_unitario": 89.90, "valor_total_item": 179.80},
    {"id_produto": 12, "codigo": "PST-0102", "nome_produto": "Pastilha de freio dianteira", "quantidade": 1, "valor_unitario": 209.90, "valor_total_item": 209.90}
  ]
}
```

**Erros:**

| Código | Mensagem |
| --- | --- |
| `400` | "Informe ao menos um item." · "A venda pode ter no máximo 30 itens." · "Um mesmo produto não pode aparecer mais de uma vez na venda." |
| `400` | "Produto inativo ou inexistente: {id}" · "Cliente inativo ou inexistente." |
| `400` | "Saldo insuficiente para {codigo}: disponível {n}, solicitado {m}." |
| `400` | "Os preços mudaram desde que o carrinho foi montado: o total agora é R$ {total}. Revise o carrinho." |
| `400` | Mensagem de conflito (corrida de estoque, preço ou chave) |
| `401` | Sessão inválida |
| `403` | Perfil sem acesso ou usuário sem funcionário vinculado |
| `429` | Limite de taxa do Xano |

### 4.5 `Balcao/detalhe_venda` (nova)

- **Entrada:** `id_transacao`. Precondição: a transação existe e é `BALCAO`.
- **Leituras:**
  - `transacoes` com `left join` em `clientes` e `funcionarios`, para os nomes;
  - `itens_transacao` da transação com `join` em `produtos`, para `codigo` e `nome_produto`, ordenados por `id`.
- Somente leitura; usada pelo `POST` (na criação e na repetição). Nenhum endpoint a expõe sozinha (D8).

### 4.6 O que não muda no Xano

- `Financeiro/resumo_operacoes`: `BALCAO` já é receita; a contraparte é o nome do cliente ou nulo.
- `transacoes` (esquema e rotas): o CRUD manual segue em `403`.
- `GET produtos` e `GET clientes`: já liberados para todos os perfis (`ALL`).
- Não há rotas genéricas para `itens_transacao` (nenhum arquivo em `xano/api`).

## 5. Reflex

### 5.1 DTOs — `Projeto_HarleyStore/services/balcao.py` (novo)

```python
MAX_ITENS_VENDA = 30

class ItemVendaBalcaoCreate(BaseModel):
    id_produto: int = Field(ge=1)
    quantidade: int = Field(ge=1)

class VendaBalcaoCreate(BaseModel):
    chave_venda: str = Field(min_length=1, max_length=64)
    id_cliente: int | None = Field(default=None, ge=1)
    total_esperado: Decimal = Field(gt=0)
    itens: list[ItemVendaBalcaoCreate] = Field(min_length=1, max_length=MAX_ITENS_VENDA)
    # validador: produtos sem repetição; total_esperado com 2 casas

class ItemVendaBalcao(BaseModel):  # extra="ignore"
    id_produto: int
    codigo: str
    nome_produto: str
    quantidade: int
    valor_unitario: Decimal
    valor_total_item: Decimal

class VendaBalcaoDetalhe(BaseModel):  # extra="ignore"
    id_transacao: int
    data_transacao: datetime
    valor_total: Decimal
    id_cliente: int | None = None
    nome_cliente: str | None = None
    id_funcionario: int
    nome_funcionario: str | None = None
    itens: list[ItemVendaBalcao] = []
```

### 5.2 `XanoClient`

```python
def vender_balcao(self, venda: VendaBalcaoCreate) -> VendaBalcaoDetalhe:
    """Counter sale (GERENTE/VENDEDOR): transaction, items and stock exit in one atomic call."""
```

Mesmo padrão de `vender_moto`: `POST balcao/vendas` com o JSON do DTO e erros tipados (`XanoValidationError`, `XanoPermissionError`, `XanoAuthenticationError`, `429`).

### 5.3 Estado — `Projeto_HarleyStore/balcao_state.py` (novo)

**Funções puras (testáveis sem Reflex):**

- `adicionar_item(carrinho, produto, quantidade)`:
  - soma ao item existente do mesmo produto;
  - recusa quantidade acima do saldo carregado e o 31º produto (`BalcaoFormError`).
- `alterar_quantidade(carrinho, produto_id, texto)` e `remover_item(carrinho, produto_id)`.
- `total_carrinho(carrinho) -> Decimal`.
- `build_venda_payload(carrinho, cliente_option, chave) -> VendaBalcaoCreate`:
  - "Consumidor final" vira `id_cliente = None`;
  - erros viram mensagens legíveis.
- `recibo_view(detalhe) -> dict`: número, data, cliente ("Consumidor final" quando nulo), vendedor, linhas e total formatados.
- `nova_chave() -> str` (`uuid.uuid4()`).

As linhas do catálogo usam `produto_row` e `filtrar_produtos`, com os mesmos campos: `id`, `codigo`, `nome`, `saldo`, `preco`, `preco_valor` e `disponivel`. A spec `arquitetura-e-contratos` proíbe um estado importar funções de outro estado de página. Por isso os dois helpers e `PRODUTO_SEARCH_LIMIT` saem de `workshop_state.py` para `listing.py`, que já tem o `normalize_text` usado pela busca. A oficina passa a importá-los de lá, sem mudar de comportamento. Esse ajuste foi identificado ao preparar o `tasks.md`.

**`BalcaoState(AuthState)`:**

- **Variáveis:** `catalogo`, `busca`, `carrinho`, `cliente_options`, `cliente`, `chave_venda`, `confirm_open`, `recibo`, `is_busy` e `list_error`.
- **Eventos:**
  - `load_balcao` (`on_load`, depois de `restore_session`; respeita `role_allows_route`): carrega produtos ativos e clientes ativos.
  - `set_busca`, `adicionar(produto_id)`, `set_quantidade(produto_id, valor)`, `remover(produto_id)`, `set_cliente` e `limpar_carrinho` (renova a chave).
  - `abrir_confirmacao`: valida pelo `build_venda_payload` e abre o painel.
  - `confirmar_venda`:
    1. trava contra reentrada, liga `is_busy` e faz `yield`;
    2. chama `vender_balcao`.

    Depois da resposta:
    - **sucesso:** mostra o recibo e um toast, limpa o carrinho, gera nova chave e recarrega os produtos;
    - **erro:** `error_feedback`, mantendo a mesma chave; em saldo, preço ou conflito, recarrega os produtos para o vendedor revisar.
  - `fechar_recibo`.

### 5.4 Página — `Projeto_HarleyStore/balcao_pages.py` (novo)

- `page_header("Venda no balcão", "Peças do estoque para clientes ou consumidor final.")`.
- Duas colunas, que viram uma só em 500 px:
  - **Peças:** filtro por categoria, `toolbar` de busca e lista dos resultados (código, nome, saldo, preço), limitada a 20 com aviso para refinar a busca. O botão "Adicionar" fica desativado como "Sem saldo" quando o saldo é zero.
  - **Carrinho:**
    - `data_table` com Produto, Preço, Quantidade (campo numérico), Subtotal e remover;
    - `labeled("Cliente", select)` com "Consumidor final" e os clientes (`option_label`);
    - `stat_tile("Total", …, accent=True)`;
    - "Limpar" (`metal_button`) e "Fechar venda" (`primary_button`, desativado com carrinho vazio ou durante o envio);
    - `empty_state("Adicione peças para iniciar a venda.")` com o carrinho vazio.
- **Confirmação (`modal_panel`):** itens, cliente e total, com "Confirmar venda" (com estado de carregamento) e "Voltar".
- **Recibo (`modal_panel`):** "Venda #N registrada", data, cliente, vendedor, itens e total, com o botão "Nova venda".
- `error_callout` para falha de carga; tudo dentro de `guarded_page(…, "/balcao")`.

### 5.5 Shell, rotas e financeiro

- `auth.py`: `ROUTE_ROLES["/balcao"] = frozenset({"GERENTE", "VENDEDOR"})`.
- `components.py`: seção "Vendas" de `NAV_SECTIONS` ganha ("Balcão", "/balcao", "shopping-cart"), rótulo "Vendas → Balcão" pedido no Apply.
- `dashboard_pages.py`: atalho "Balcão" em `SHORTCUTS`, filtrado pelo perfil como os demais.
- `Projeto_HarleyStore.py`: `app.add_page(balcao_page, route="/balcao", title="Venda no balcão | Harley Store", on_load=[AuthState.restore_session, BalcaoState.load_balcao])`.
- `financeiro_state.py`:
  - `descricao_operacao` devolve "Venda no balcão #N" para `BALCAO`;
  - em `operacao_row`, a contraparte nula de uma `BALCAO` aparece como "Consumidor final".

## 6. Matriz de acesso (alterações)

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Vender no balcão (`/balcao`, `POST balcao/vendas`) | sim | sim | não |
| Ver as vendas no balcão (`/financeiro`, `GET financeiro/resumo`) | sim | não | não |
| Listar produtos e clientes para o carrinho (`GET produtos`, `GET clientes`) | sim | sim | sim (sem mudança) |

## 7. Plano de testes

| Arquivo | Cobertura |
| --- | --- |
| `tests/test_balcao_contracts.py` (novo) | **Esquema:** `itens_transacao` com chaves estrangeiras, mínimos e índice único `(chave_venda, id_produto)`; `movimentacoes_estoque` com `SAIDA_VENDA` e `id_transacao` (FK e `btree`). **`movimentar_estoque`:** subtrai e exige produto ativo em `SAIDA_VENDA`; os tipos antigos não mudam. **Endpoint:** `enforce_role "VENDEDOR"`; autor do JWT; entrada sem preço nem total por item; limites 1 a 30; pré-validações (repetição, saldo, cliente, total) antes do `try_catch`; `db.transaction` com `transacoes` `BALCAO`, itens em ordem de `id_produto` e `movimentar_estoque` `SAIDA_VENDA` com `id_transacao`; total conferido dentro; `catch` com a mensagem de conflito. **`detalhe_venda`:** somente leitura. **Rotas:** nenhuma rota genérica para `itens_transacao`. |
| `tests/test_balcao.py` (novo) | **DTOs:** limites, produto repetido, quantidade e total positivos, chave obrigatória, decimais e detalhe com cliente nulo. **`XanoClient.vender_balcao`:** rota, JSON, token e erros tipados (`400`, `403`, `429`) com `MockTransport`. |
| `tests/test_balcao_state.py` (novo) | **Carrinho:** soma do mesmo produto, limite de saldo e de 30 itens, alterar, remover e total. **Payload:** consumidor final e cliente, com mensagens. **Chave:** mantida após erro, renovada após sucesso ou limpeza. **Acesso:** carga só para `GERENTE` e `VENDEDOR`. **`confirmar_venda` (via `run_event`):** `yield` antes da chamada, recibo, recarga dos produtos e erros de saldo e preço visíveis com recarga. |
| `tests/test_loading_states.py` | `confirmar_venda` entra na regra "`yield` antes do Xano". |
| `tests/test_financeiro_state.py` | "Venda no balcão #N" e "Consumidor final". |
| `tests/test_security_contracts.py` / `test_hardening_contracts.py` | Matriz com `/balcao`; ampliação do enum de `movimentar_estoque`; nenhuma rota de escrita genérica nova. |
| `tests/test_layout.py` | 14 rotas com o logo. |
| `tests/test_workshop_state.py` | `produto_row` e `filtrar_produtos` importados de `listing.py`, com o mesmo comportamento. |
| `tests/test_integration_xano.py` | **Sem escrita:** `MECANICO` recebe `403`; payload inválido recebe `400`. **Com escrita:** venda com cliente e com consumidor final (transação, itens, livro com `id_transacao`, saldo e presença no resumo); saldo insuficiente e total divergente sem efeito; repetição da chave devolve a mesma venda. **Concorrência:** duas vendas da última unidade resultam em uma aceita e saldo zero. |

Verificação antes do Archive:

- suíte `pytest`;
- `python -m py_compile`;
- `reflex compile --dry`;
- validador XanoScript em todos os `.xs` alterados;
- `xano workspace push --dry-run`.

## 8. Documentação e specs

- **`docs/domain-model.md`:**
  - nova seção *Itens_Transacao*;
  - *Transacoes*: origem `BALCAO` e itens; sai a frase "transações não possuem linhas de itens";
  - *Movimentacoes_Estoque*: `SAIDA_VENDA` e `id_transacao`.
- **`docs/xano-api-client.md`:** `vender_balcao`, DTOs, matriz e checklist de deploy da Change 11.
- **`docs/project-structure.md`:** `balcao_state.py`, `balcao_pages.py` e `services/balcao.py`.
- **Specs (deltas em `specs/` desta change, aplicados no arquivamento):**
  - nova `vendas-balcao.md`;
  - deltas em `estoque-entradas.md` (saída por venda), `financeiro.md` (receita `BALCAO`) e `arquitetura-e-contratos.md` (rota, matriz e imutabilidade dos itens).

## 9. Deploy e riscos

- **Push:**
  - aditivo: tabela, campo, índices, função e endpoint;
  - com ampliação de enum (D10);
  - publicar o Xano antes do Reflex, porque a tela chama uma rota nova;
  - o plano Free publica na hora: revisar o `--dry-run`, com OK antes da mudança de banco e antes do push.
- **Resultado do `--dry-run` (2026-10-09, D10):**
  - Change 11: `CREATE table itens_transacao`, `UPDATE`/`ADD_FIELD`/`UPDATE_FIELD table movimentacoes_estoque`, `CREATE function Balcao/detalhe_venda`, `UPDATE function Estoque/movimentar_estoque` e `CREATE query balcao/vendas POST`;
  - nenhuma exclusão e nenhum pedido de `--sync`;
  - também aparece `UPDATE table modelos_moto`, divergência anterior (Change 8: `destaque?=false` local, sem padrão no remoto), que os pushes parciais nunca aplicaram;
  - por isso, conferir depois do push, com um `pull`, que o enum recebeu `SAIDA_VENDA`.
- **Observação fora do escopo:** `entrada_mercadoria_POST` (`|sort:"id_produto":"int":false`) e `Financeiro/resumo_operacoes` (`|sort:"data":"number":false`) usam o mesmo filtro com sentidos opostos nos comentários ("ordem de produto" e "mais recentes primeiro"). Pela documentação do filtro, um dos dois está invertido. Vale verificar numa Change de saneamento; o balcão não depende disso.
- **Plano Free:** uma venda de 30 itens faz cerca de 150 operações numa transação. O limite de D9 e o tratamento de `429` na tela mantêm uma chamada por fechamento.
- **Carrinho sem reserva:** outra venda ou uma OS pode consumir o saldo entre a montagem e o fechamento. O fechamento recusa com a mensagem de saldo e a tela recarrega os produtos.
- **Produtos com saldo nulo (débito 5):** tratados como 0, em linha com `movimentar_estoque`.
- **Integração pendente:** a integração com escrita das Changes 5 a 10 ainda não rodou contra o Xano real. Os cenários desta Change dependem das mesmas credenciais (`XANO_TEST_*`).

## 10. Fora do escopo

Ver a proposta: estorno e devolução, desconto, pagamento e caixa, nota fiscal, vínculo com moto do cliente, consultas de vendas pelo vendedor, uso automático de `PECAS`, serviços no balcão e reserva de estoque.
