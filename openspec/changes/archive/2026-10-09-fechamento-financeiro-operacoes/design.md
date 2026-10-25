# Design: fechamento financeiro e visão consolidada das operações (Change 10)

> **Situação:** Apply concluído e verificado em 2026-10-09; aguarda o push do Xano, o lançamento retroativo e a integração para o arquivamento. As decisões D1 a D10 foram aprovadas como recomendadas.

## 1. Origem do escopo

Nenhum documento numera a Change 10. O escopo vem das pendências que as Changes anteriores deixaram, explicitamente, para uma "Change de fechamento financeiro":

| Fonte | Pendência |
| --- | --- |
| `docs/project-overview.md` §3 e relatório do projeto (PDF) | "Oferecer uma visão consolidada das operações financeiras e entradas de mercadorias." |
| `docs/domain-model.md` → *Visão Consolidada* | `vw_resumo_operacoes` "unifica as Transações Comerciais e as Entradas de Mercadorias"; ainda não existe. |
| `openspec/archive/itens-os-baixa-estoque/proposal.md` (Change 7) | "O lançamento em `transacoes` (`ORDEM_SERVICO`) na conclusão … fica para a Change de fechamento financeiro." |
| `openspec/archive/entrada-mercadoria-estoque-atomico/proposal.md` (Change 5, D6) | Sem transação `COMPRA` na entrada de mercadoria. |
| `docs/auditoria-arquitetura-changes-1-7.md`, débito 3 (prioridade alta) | "Redesenhar `transacoes`: imutável, valores calculados no servidor, sem `PUT`/`PATCH` livres." Continua pendente. |
| `openspec/archive/fechamento-venda-motos/proposal.md` (Change 9) | Redesenho de `transacoes` e "telas de consulta financeira" ficaram fora do escopo. |

Estado atual confirmado no código:

- `xano/api/harley/transacoes_*.xs` é um CRUD genérico. O saneamento pós-Change 9 (2026-10-09) já o restringiu:
  - `GET` e `GET {id}` somente para `GERENTE` (antes: todos os perfis);
  - `POST`, `PUT` e `PATCH` somente para `GERENTE` (antes: `VENDEDOR`), ainda com `tipo_transacao`, `valor_total` e `data_transacao` vindos do payload; o `PUT` preserva o autor;
  - só o `DELETE` está bloqueado.
- O Reflex não usa `transacoes`; a única transação gerada por regra de negócio é a `MOTO` da venda (Change 9).
- Concluir uma OS (`POST ordens_servico/{id}/status`) não gera lançamento financeiro.
- Não há tela financeira; `/admin` é um marcador.

A venda no balcão (`BALCAO`/`PECAS` com baixa de estoque) também é um objetivo em aberto, mas depende de itens de transação, uma decisão de modelagem ainda pendente (`domain-model.md`). Ela fica para a Change 11 (D1).

## 2. Objetivo, regras e módulos afetados

**Objetivo:** tornar `transacoes` um registro financeiro confiável e dar ao gerente uma visão consolidada de receitas e despesas por período.

**Regras de negócio:**

1. Concluir uma OS com total maior que zero lança uma transação `ORDEM_SERVICO` com o total da OS, na mesma transação da conclusão.
2. Transações são imutáveis e nascem somente de operações de negócio (venda de moto e conclusão de OS); não há criação, edição nem exclusão manual.
3. A visão consolidada une transações (receitas) e entradas de mercadoria (despesas) num período, com totais por tipo e saldo.
4. Somente o `GERENTE` consulta dados financeiros.

**Módulos afetados:**

| Módulo | Impacto |
| --- | --- |
| Oficina / Ordens de serviço | Conclusão gera o lançamento; o detalhe mostra a transação; o painel de transição avisa o valor. |
| Transações / Financeiro | Esquema (`id_os`), bloqueio do CRUD, função e endpoint do resumo, tela `/financeiro`. |
| Estoque / Entradas | Somente leitura: as entradas entram no resumo como despesas. Nenhuma mudança de estoque. |
| Vendas de motos | Nenhuma mudança: as transações `MOTO` da Change 9 entram no resumo como estão. |
| Shell, autenticação e dashboard | Rota `/financeiro` (GERENTE), item de navegação, atalho no dashboard, tokens de cor. |

## 3. Decisões

- **D1 — Escopo:** fechamento financeiro (lançamento da OS, imutabilidade e visão consolidada). Venda no balcão vai para a Change 11, que reutilizará o resumo. *Recomendado.* A alternativa é incluir o balcão agora: exige itens de transação e um novo tipo de movimentação de estoque, e dobra o tamanho da Change.
- **D2 — Lançamento da OS:** na transição para `CONCLUIDA`, dentro da `db.transaction` existente, com `valor_total` recalculado por `Oficina/totais_os`. Uma OS com total zero (garantia, cortesia) conclui sem lançamento. *Recomendado.* A alternativa é impedir a conclusão de OS com total zero.
- **D3 — Autoria do lançamento:** `id_funcionario` = quem concluiu a OS (JWT), como em todas as autorias. *Recomendado.*
- **D4 — Entradas não geram `COMPRA`:** a visão consolidada lê `entrada_mercadoria` diretamente, como define `vw_resumo_operacoes`. Isso evita contar duas vezes e dispensa preencher entradas antigas. `COMPRA` fica sem uso automático; transações `COMPRA` antigas, se existirem, contam como despesa. *Recomendado.* A alternativa é gravar `COMPRA` em cada entrada nova, com uma função para preencher as antigas, e ler só `transacoes`.
- **D5 — Imutabilidade:** `POST transacoes`, `PUT` e `PATCH transacoes/{id}` passam a `403`, preservando rota e `guid` (padrão já usado no `DELETE`). Correção de lançamento será um estorno numa Change futura. *Recomendado.*
- **D6 — Acesso:** `GET transacoes` e `GET transacoes/{id}` só para `GERENTE` (já aplicado pelo saneamento pós-Change 9); o resumo e a tela `/financeiro` também. *Recomendado.*
- **D7 — Limites do resumo:**
  - período obrigatório, de no máximo 366 dias;
  - os totais cobrem o período inteiro;
  - a lista traz as 500 operações mais recentes, com o indicador `truncado`.

  *Recomendado* por causa do plano Free do Xano e do limite de `429`.
- **D8 — Sem índice único em `transacoes.id_os`:** a máquina de estados já garante um lançamento por OS, porque o índice único `(id_os, status_anterior)` deixa a OS sair de `EM_ANDAMENTO` uma única vez. Um índice único com milhares de linhas nulas dependeria de o Xano tratar nulos como distintos, o que ainda não foi verificado (é o mesmo risco da placa na Change 9). Fica um `btree` simples. *Recomendado.*
- **D9 — Fuso do período:** os limites de cada dia são calculados no Reflex em UTC−3 fixo (o Brasil não tem horário de verão desde 2019) e enviados como timestamps. Assim não é preciso a dependência `tzdata`, que não está instalada. *Recomendado.*
- **D10 — OS concluídas antes da Change 10:** função idempotente `Financeiro/lancar_os_concluidas_legadas`, executada uma vez pelo Run & Debug, como `Estoque/normalizar_entradas_legadas`. Lança cada OS `CONCLUIDA` com total maior que zero e sem transação, usando `data_encerramento` (ou `data_abertura`) como data. *Recomendado.* A alternativa é o resumo mostrar só o que foi concluído depois do push.

## 4. Visão geral

```text
Oficina ─ confirm_transition ─► POST ordens_servico/{id}/status  (CONCLUIDA)
                                 db.transaction:
                                   historico_status_os → patch OS → Oficina/totais_os
                                   └ total > 0 → db.add transacoes (ORDEM_SERVICO, id_os)

/financeiro (GERENTE) ─ FinanceiroState ─ XanoClient.resumo_financeiro ─► GET financeiro/resumo
                                                                           └ Financeiro/resumo_operacoes
                                                                               transacoes (receitas)
                                                                             ∪ entrada_mercadoria (despesas)

transacoes: POST / PUT / PATCH / DELETE ─► 403   ·   GET ─► GERENTE
```

As regras continuam no Xano. O Reflex só valida o período para dar retorno imediato e formata os dados.

## 5. Xano

### 5.1 Esquema `transacoes`

```xs
// OS faturada (Change 10). Nulo nas demais transações.
int? id_os? {
  table = "ordens_servico"
}
```

- Índice novo: `{type: "btree", field: [{name: "id_os"}]}` (D8).
- Alteração aditiva (campo anulável): não exige `--sync`.

### 5.2 `POST ordens_servico/{id}/status` (alteração)

- A leitura da OS passa a trazer `id_cliente` e `id_moto_cliente`; o cliente da transação é `$os.id_cliente ?? motos_clientes.id_cliente` (OS anteriores à Change 6).
- Dentro da `db.transaction`, depois do `db.patch ordens_servico`:

```xs
conditional {
  if ($input.status_novo == "CONCLUIDA") {
    function.run "Oficina/totais_os" {
      input = {os_id: $input.ordens_servico_id}
    } as $totais

    conditional {
      if ($totais.valor_total > 0) {
        db.add transacoes {
          data = {
            tipo_transacao : "ORDEM_SERVICO"
            id_funcionario : $auth_user.id_funcionario
            id_cliente     : $id_cliente
            id_moto_cliente: $os.id_moto_cliente
            id_os          : $input.ordens_servico_id
            data_transacao : $agora
            valor_total    : $totais.valor_total
          }
        } as $transacao
      }
    }
  }
}
```

- O `patch` anterior atualiza `atualizado_em` e trava a OS: nenhuma inclusão ou remoção de item concorrente altera o total entre o cálculo e o lançamento.
- Qualquer falha cai no `try_catch` atual: nada é gravado e a resposta é `400` com a mensagem existente.
- A resposta continua sendo o detalhe da OS.

### 5.3 `Oficina/detalhe_os` (alteração)

Consulta `transacoes` por `id_os` e acrescenta ao detalhe `id_transacao` (ou nulo) e `data_lancamento`.

### 5.4 Bloqueio do CRUD de `transacoes`

| Rota | Antes | Depois |
| --- | --- | --- |
| `GET transacoes` | `GERENTE`, ordenado por `data_transacao` desc (saneamento) | sem mudança |
| `GET transacoes/{id}` | `GERENTE` (saneamento) | sem mudança |
| `POST transacoes` | `GERENTE`, payload livre (saneamento) | `403` "Transações são registradas somente pelas operações de venda e de oficina." |
| `PUT` / `PATCH transacoes/{id}` | `GERENTE`, autor preservado (saneamento) | `403` "Transações são imutáveis." |
| `DELETE transacoes/{id}` | `403` (mensagem já atualizada no saneamento) | sem mudança |

As rotas bloqueadas mantêm `enforce_role` antes do `precondition (false)`, rota e `guid`, como os demais bloqueios do projeto.

### 5.5 `GET financeiro/resumo` (novo)

- **Arquivo:** `xano/api/harley/financeiro/resumo_GET.xs` (grupo `HARLEY`, `auth = "user"`).
- **Perfil:** `GERENTE` (`enforce_role`).
- **Implementação:** chama `Financeiro/resumo_operacoes` (equivalente ao `vw_resumo_operacoes`).

**Entrada (query string):**

| Campo | Tipo | Regra |
| --- | --- | --- |
| `inicio` | timestamp (ms) | obrigatório |
| `fim` | timestamp (ms) | obrigatório; `fim >= inicio`; `fim − inicio ≤ 366 dias` |

**Saída (`200`):**

```json
{
  "inicio": 1790823600000,
  "fim": 1793501999999,
  "receitas": 235400.00,
  "despesas": 18250.50,
  "saldo": 217149.50,
  "por_tipo": [
    {"tipo": "MOTO", "natureza": "RECEITA", "quantidade": 1, "valor": 185000.00},
    {"tipo": "ORDEM_SERVICO", "natureza": "RECEITA", "quantidade": 12, "valor": 50400.00},
    {"tipo": "ENTRADA_MERCADORIA", "natureza": "DESPESA", "quantidade": 3, "valor": 18250.50}
  ],
  "operacoes": [
    {
      "origem": "TRANSACAO", "id": 41, "tipo": "ORDEM_SERVICO", "natureza": "RECEITA",
      "data": 1791990000000, "valor": 1250.00,
      "contraparte": "Ana Souza", "funcionario": "João Mecânico",
      "id_os": 87, "id_moto_cliente": 30, "modelo": "Street Glide", "placa": "ABC1D23",
      "id_entrada": null, "numero_documento": null
    },
    {
      "origem": "ENTRADA", "id": 12, "tipo": "ENTRADA_MERCADORIA", "natureza": "DESPESA",
      "data": 1791900000000, "valor": 8200.00,
      "contraparte": "Distribuidora Moto Peças", "funcionario": "Gerente",
      "id_os": null, "id_moto_cliente": null, "modelo": null, "placa": null,
      "id_entrada": 12, "numero_documento": "NF-5521"
    }
  ],
  "total_operacoes": 16,
  "truncado": false
}
```

**Natureza por tipo:** `MOTO`, `ORDEM_SERVICO`, `PECAS` e `BALCAO` são `RECEITA`; `COMPRA` (antigas) e `ENTRADA_MERCADORIA` são `DESPESA`. `por_tipo` só traz os tipos com operações no período.

**Algoritmo de `Financeiro/resumo_operacoes`:**

1. Validar o período:
   - `400` "O fim do período deve ser igual ou posterior ao início.";
   - `400` "O período pode ter no máximo 366 dias.".
2. `db.query transacoes`:
   - filtro `data_transacao` entre `inicio` e `fim`;
   - `left join` com `clientes`, `funcionarios` e `motos_clientes`, e `eval` dos nomes, do modelo e da placa (padrão de `Oficina/detalhe_os`).
3. `db.query entrada_mercadoria`:
   - filtro `data_entrada` no período;
   - `left join` com `fornecedores` e `funcionarios`.
4. Um `foreach` em cada lista monta as operações e acumula `por_tipo`, `receitas` e `despesas`, com `round:2`.
5. Ordenar as operações por `data` desc, guardar o total em `total_operacoes` e cortar em 500 (`|slice`); `truncado = total_operacoes > 500`.

Sem escrita, sem `db.transaction`.

**Erros:** `400` (período), `401`, `403` (perfil), `429`.

### 5.6 `Financeiro/lancar_os_concluidas_legadas` (nova, D10)

- **Entrada:** `id_funcionario` de um `GERENTE`, informado no Run & Debug; é o autor dos lançamentos retroativos.
- Percorre as OS `CONCLUIDA` sem transação com `id_os` igual e, para cada uma com `Oficina/totais_os.valor_total > 0`, grava a transação `ORDEM_SERVICO` com `data_transacao = data_encerramento ?? data_abertura`.
- **Idempotente:** executar de novo não duplica.
- **Resposta:** quantidade lançada e ids ignorados (total zero).
- Não é chamada por nenhum endpoint (como `seed_gerente`).

## 6. Reflex

### 6.1 DTOs — `Projeto_HarleyStore/services/financeiro.py` (novo)

```python
TipoOperacao = Literal["MOTO", "PECAS", "BALCAO", "ORDEM_SERVICO", "COMPRA", "ENTRADA_MERCADORIA"]
Natureza = Literal["RECEITA", "DESPESA"]
TIPO_LABELS = {
    "MOTO": "Venda de moto", "ORDEM_SERVICO": "Serviço de oficina", "PECAS": "Peças",
    "BALCAO": "Balcão", "COMPRA": "Compra", "ENTRADA_MERCADORIA": "Entrada de mercadoria",
}
NATUREZA_POR_TIPO: dict[str, Natureza]  # espelho da regra do Xano
PERIODO_MAXIMO_DIAS = 366
FUSO_LOJA = timezone(timedelta(hours=-3), "BRT")  # D9

class PeriodoFinanceiro(BaseModel):
    inicio: date
    fim: date
    # validadores: fim >= inicio; (fim - inicio).days < PERIODO_MAXIMO_DIAS
    def params(self) -> dict[str, int]: ...  # inicio 00:00 e fim 23:59:59.999 em FUSO_LOJA, em ms

class TotalPorTipo(BaseModel):
    tipo: TipoOperacao
    natureza: Natureza
    quantidade: int
    valor: Decimal

class OperacaoFinanceira(BaseModel):  # extra="ignore"
    origem: Literal["TRANSACAO", "ENTRADA"]
    id: int
    tipo: TipoOperacao
    natureza: Natureza
    data: datetime
    valor: Decimal
    contraparte: str | None = None
    funcionario: str | None = None
    id_os: int | None = None
    id_moto_cliente: int | None = None
    modelo: str | None = None
    placa: str | None = None
    id_entrada: int | None = None
    numero_documento: str | None = None

class ResumoFinanceiro(BaseModel):
    inicio: datetime
    fim: datetime
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
    por_tipo: list[TotalPorTipo] = []
    operacoes: list[OperacaoFinanceira] = []
    total_operacoes: int = 0
    truncado: bool = False
```

`FUSO_LOJA` fica em `formatting.py` se outro módulo precisar dele; `format_datetime` não muda.

### 6.2 `XanoClient`

```python
def resumo_financeiro(self, periodo: PeriodoFinanceiro) -> ResumoFinanceiro:
    """Consolidated view (GERENTE): transactions and goods receipts in the period."""
    return self.get("financeiro/resumo", params=periodo.params(), response_model=ResumoFinanceiro)
```

Nenhum método de escrita para transações (D5).

### 6.3 Ordens de serviço

- `OrdemServicoDetalhe` ganha `id_transacao: int | None = None` e `data_lancamento: datetime | None = None`.
- No detalhe da OS (`workshop_detail.py`):
  - OS concluída com lançamento: "Faturada · transação #N · data".
  - OS concluída com total zero: "Concluída sem lançamento financeiro (total zero)".
  - OS concluída antes do push e ainda não lançada: o mesmo aviso, até rodar a função de D10.
- No painel de transição (`transition_panel`), quando o alvo é `CONCLUIDA`: "O total de R$ X será lançado como receita de serviço." Com total zero: "Total zero: a OS será concluída sem lançamento."
- `WorkshopState` não muda o fluxo; a resposta da transição já traz o detalhe atualizado.

### 6.4 Página `/financeiro` (nova)

**`Projeto_HarleyStore/financeiro_state.py`**

- `FinanceiroState(AuthState)`:
  - período: `inicio`, `fim` (texto `AAAA-MM-DD`; padrão: primeiro dia do mês corrente até hoje, em `FUSO_LOJA`);
  - dados: `resumo` (totais formatados), `por_tipo`, `operacoes` (linhas `dict[str, str]`);
  - filtros e estado da tela: `filtro_tipo`, `busca`, `list_error`, `is_loading`.
- Funções puras e testáveis:
  - `periodo_padrao(hoje)`, `atalho_periodo(nome, hoje)` (`MES_ATUAL`, `MES_ANTERIOR`, `ULTIMOS_30_DIAS`);
  - `build_periodo(inicio, fim)`, que gera `FinanceiroFormError` com mensagens legíveis;
  - `descricao_operacao(op)` monta o texto:
    - `MOTO`: "Venda de moto · Street Glide · ABC1D23";
    - `ORDEM_SERVICO`: "OS #87 · Street Glide";
    - `ENTRADA_MERCADORIA`: "Entrada NF-5521";
    - transações antigas: "Transação #N".
  - `operacao_row(op)` e `filtrar_operacoes(rows, tipo, busca)`, com filtro local para não chamar o Xano de novo.
- Eventos:
  - `load_financeiro` (`on_load`, depois de `restore_session`; respeita `role_allows_route`);
  - `set_inicio` e `set_fim`;
  - `aplicar_periodo`, que valida e recarrega;
  - `usar_atalho(nome)`;
  - `set_filtro_tipo` e `set_busca`.
- Erros pelo `feedback.error_feedback`, com `429` e sessão expirada tratados como nas demais telas.

**`Projeto_HarleyStore/financeiro_pages.py`**

- `page_header("Financeiro", "Receitas, despesas e saldo do período.")`.
- Barra de período: dois `rx.input(type="date")`, os botões de atalho (`metal_button`) e "Aplicar" (`primary_button`).
- Linha de `stat_tile`: Receitas, Despesas e Saldo (`accent`). O saldo negativo usa a cor `danger`.
- "Por tipo": `data_table` com tipo, natureza, quantidade e valor.
- "Operações": abas roláveis por tipo (`rx.tabs`, como as famílias do catálogo; no Apply substituíram o `rx.segmented_control`, que não cabia em 500 px com os rótulos longos), `toolbar` de busca e `data_table` com Data, Tipo (`status_badge` por natureza), Descrição, Cliente/Fornecedor, Funcionário e Valor (à direita; despesas com `−` e na cor de perigo).
- Quando `truncado`: aviso "Mostrando as 500 operações mais recentes de N; os totais cobrem o período inteiro."
- `empty_state` sem operações e `error_callout` para erro.
- Tudo dentro de `guarded_page(…, "/financeiro")`.

**Shell, rotas e tema:**

- `auth.py`: `ROUTE_ROLES["/financeiro"] = {"GERENTE"}`.
- `components.py`: seção "Gestão" em `NAV_SECTIONS` com ("Financeiro", "/financeiro", "chart-column"), antes de "Administração".
- `dashboard_pages.py`: atalho "Financeiro" em `SHORTCUTS`, visível só ao gerente pelo filtro existente.
- `Projeto_HarleyStore.py`: `app.add_page(financeiro_page, route="/financeiro", title="Financeiro | Harley Store", on_load=[AuthState.restore_session, FinanceiroState.load_financeiro])`.
- `styles/theme.py`: `STATUS_COLORS` ganha `RECEITA` (verde) e `DESPESA` (vermelho escuro com texto claro). Os pares entram em `TEXT_PAIRS` e no teste de contraste WCAG.

## 7. Matriz de acesso (alterações)

| Operação | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Concluir OS (gera lançamento) | sim | não | sim |
| Consultar transações (`GET transacoes`) | sim | não (antes: sim) | não (antes: sim) |
| Criar, editar ou excluir transação manualmente | não | não (antes: sim) | não |
| Visão consolidada (`/financeiro`, `GET financeiro/resumo`) | sim | não | não |

## 8. Testes

| Arquivo | Cobertura |
| --- | --- |
| `tests/test_financeiro_contracts.py` (novo) | `transacoes.id_os` anulável com `btree` não único; `POST`/`PUT`/`PATCH transacoes` em `403` com `enforce_role` e `guid` preservado; `GET` com `GERENTE`; lançamento só em `CONCLUIDA`, dentro da `db.transaction`, depois do `patch`, com `totais_os`, `valor_total > 0` e `id_funcionario` do JWT; resumo com `GERENTE`, validação do período, junção das duas fontes, `slice` 500 e sem escrita; função de D10 idempotente e fora dos endpoints. |
| `tests/test_financeiro.py` (novo) | `PeriodoFinanceiro` (ordem, 366 dias, `params` em UTC−3 com fim às 23:59:59.999); DTOs com campos nulos e decimais; `XanoClient.resumo_financeiro`: rota, query string, token e erros tipados (`MockTransport`). |
| `tests/test_financeiro_state.py` (novo) | período padrão e atalhos; `build_periodo` com mensagens; `descricao_operacao` por tipo; filtro local; carga só para `GERENTE`; erro e `429` visíveis; saldo negativo. |
| `tests/test_ordens_servico*.py` | `OrdemServicoDetalhe.id_transacao`; mensagens do painel de conclusão (total e total zero). |
| `tests/test_hardening_contracts.py` / `test_security_contracts.py` | atualização da lista de rotas bloqueadas e da matriz. |
| `tests/test_layout.py` | 13 rotas com o logo. |
| `tests/test_theme.py` | contraste de `RECEITA`/`DESPESA`. |
| `tests/test_integration_xano.py` | sem escrita: `VENDEDOR` e `MECANICO` recebem `403` no resumo e no `GET transacoes`; `POST transacoes` recebe `403`; período inválido `400`. Com escrita: concluir uma OS com itens gera uma única transação `ORDEM_SERVICO` com o total e aparece no resumo; OS sem itens conclui sem transação. Com concorrência: duas conclusões simultâneas geram uma transação. |

## 9. Documentação

- `docs/domain-model.md`: seção *Transacoes* (origem, imutabilidade e `id_os`), *Visão Consolidada* (regras de D4 e D7) e conclusão da OS.
- `docs/xano-api-client.md`: `resumo_financeiro`, DTOs, matriz, checklist de deploy da Change 10 e testes.
- `docs/project-structure.md`: `financeiro_state.py`, `financeiro_pages.py` e `services/financeiro.py`.
- Specs: nova `openspec/specs/financeiro.md` (lançamento, imutabilidade, resumo e acesso) e delta em `oficina-ordens-servico.md` (conclusão gera lançamento).

## 10. Deploy e riscos

- **Push:** aditivo (campo e índice em `transacoes`, função, endpoint), mais alterações de endpoints existentes; sem `--sync`. Revisar o `--dry-run` antes, porque o plano Free publica na hora.
- **Depois do push:** executar `Financeiro/lancar_os_concluidas_legadas` uma vez (D10) e rodar a integração.
- **Transações antigas do CRUD genérico:** podem ter valores e datas arbitrários e entram no resumo como estão. O gerente deve conferi-las antes de usar o resumo como fechamento. Não há exclusão (D5).
- **Volume:** o resumo lê o período inteiro a cada chamada. Os limites de D7 mantêm uma chamada por consulta; a tela não refaz a chamada ao filtrar por tipo ou buscar.
- **Pendências anteriores:** a integração com escrita das Changes 5 a 9 ainda não rodou contra o Xano real. O resultado da Change 9 sobre placas nulas no índice único confirma ou derruba a premissa de D8.

## 11. Fora do escopo

- Venda no balcão (`BALCAO`/`PECAS`), itens de transação e baixa de estoque por venda (Change 11).
- Estorno de transações, de vendas e de entradas.
- Forma de pagamento, parcelas, contas a receber e a pagar, nota fiscal.
- Comissões, custo médio e margem por produto.
- Exportação (CSV ou PDF) e gráficos; a primeira versão é tabular.
- Tela de administração de usuários (`/admin`).
