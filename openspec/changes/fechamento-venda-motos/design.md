# Design: fechamento de vendas de motos (Change 9)

## Visão geral

```text
/vendas ─ VendasState ─ open_venda ─────► list_clientes (clientes ativos)
                      └ confirm_venda ──► XanoClient.vender_moto ─► POST vender_moto (VENDEDOR)
                           │                                        └ Vendas/vender_moto
                           │                                            pré-checagens (404/400)
                           │                                            db.transaction:
                           │                                              motos_clientes + transacoes (MOTO)
                           │                                              Vendas/transicionar_moto → VENDIDA
                           ├ sucesso: catalogo_cache.invalidate() + recarga da lista (+ detalhe aberto)
                           └ recusa:  recarga da lista; fecha o modal se a unidade não é mais vendável
```

As regras continuam no Xano. O Reflex valida antes de enviar só para dar retorno imediato.

## Contrato: `POST /api:harley/vender_moto`

- **Grupo:** `HARLEY`. **Autenticação:** `auth = "user"` (JWT no cabeçalho `Authorization: Bearer`).
- **Perfis:** `VENDEDOR` e `GERENTE` (`Quick Start/enforce_role` com `required_role: "VENDEDOR"`).
- **Funcionário:** resolvido por `$auth.id → user.id_funcionario`. O payload não aceita `id_funcionario`.

### Entrada (JSON)

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id_moto` | int | sim | `≥ 1`; unidade de `motos` |
| `id_cliente` | int | sim | `≥ 1`; cliente ativo |
| `valor_venda` | decimal | sim | `≥ 0,01` (até duas casas no Reflex) |
| `placa` | text | não | `trim` + caixa alta; vazio vale como ausente; única em `motos_clientes` quando informada |
| `observacao` | text | não | `trim`, até 500 caracteres; vira a observação do histórico (padrão "Venda") |

### Saída (`200`)

```json
{"id_transacao": 41, "id_moto_cliente": 87, "status": "SUCESSO"}
```

### Efeitos (uma única `db.transaction`)

1. `motos_clientes`: `id_cliente`, `modelo` (nome do modelo comercial; em unidades legadas, `modelo`/`marca`), `placa` (ou nulo), `chassi` da unidade e `ativo = true`.
2. `transacoes`: `tipo_transacao = MOTO`, `id_funcionario` do JWT, `id_cliente`, `id_moto_cliente`, `data_transacao = now`, `valor_total = valor_venda`.
3. `historico_status_moto` e `motos` por `Vendas/transicionar_moto`: `status_esperado` = status lido, `status_novo = VENDIDA`, `clientes_id` = comprador; reserva (vendedor e validade) zerada.

Qualquer falha dentro da transação desfaz os três passos.

### Erros

| HTTP | Situação | Mensagem do Xano |
| --- | --- | --- |
| `400` | entrada fora do contrato (ex.: `valor_venda` ≤ 0) | validação de input do Xano |
| `400` | unidade já vendida | "Esta moto já foi vendida." |
| `400` | unidade reservada para outro cliente | "Esta moto está reservada para outro cliente." |
| `400` | unidade sem chassi | "Cadastre o chassi desta moto antes de vendê-la." |
| `400` | cliente inativo ou inexistente | "Cliente inativo ou inexistente." |
| `400` | chassi já em `motos_clientes` | "Chassi já cadastrado em uma moto de cliente." |
| `400` | placa já em `motos_clientes` | "Placa já cadastrada em uma moto de cliente." |
| `400` | outra transição venceu a corrida (índice único de versão) | "A moto foi alterada por outro usuário. Atualize e tente novamente." |
| `401` | JWT ausente ou expirado | — |
| `403` | perfil sem permissão ou usuário sem funcionário | "Seu usuário não está vinculado a um funcionário." |
| `404` | unidade inexistente | "Moto não encontrada." |
| `429` | limite de requisições do workspace | — |

## Concorrência

A venda reutiliza o mecanismo da Change 8: `Vendas/transicionar_moto` grava o histórico com `versao_anterior` antes de atualizar a moto, e o índice único `(id_moto, versao_anterior)` faz a segunda transição concorrente falhar. O `try_catch` em volta da `db.transaction` converte a falha em `400` com mensagem amigável e desfaz a moto do cliente e a transação já inseridas.

No Reflex, uma recusa `400` ou `404` recarrega a lista. Se a unidade não estiver mais vendável para o cliente escolhido (vendida, reservada para outro, removida), o modal fecha e a notificação mostra a mensagem do Xano; a linha já aparece com o novo status. Se ainda for vendável (ex.: placa duplicada), o modal continua aberto com o erro.

## Placa opcional

- `motos_clientes.placa` passa a `text? placa?`. O índice `btree|unique` continua: valores nulos não colidem entre si.
- `vender_moto` normaliza vazio para nulo e só consulta a placa quando ela existe; o chassi é sempre checado. A consulta anterior (`placa == $input.placa || chassi == …`) casaria todas as motos sem placa.
- No Reflex, `MotoCliente.placa` aceita nulo, a coluna mostra vazio e o formulário de Cadastros trata placa em branco como ausente.

## Reflex

### DTOs (`services/motos.py`)

- `VendaMotoCreate`: `id_moto > 0`, `id_cliente > 0`, `valor_venda > 0` com duas casas, `placa` opcional normalizada (`trim`, caixa alta, sem hífen ou espaços, padrão antigo `ABC1234` ou Mercosul `ABC1D23`; vazio → `None`), `observacao` até 500. Não tem `id_funcionario`.
- `VendaMotoResultado`: `id_transacao`, `id_moto_cliente`, `status`.

### Cliente (`services/xano_client.py`)

`vender_moto(venda) -> VendaMotoResultado` faz `POST vender_moto` com `model_dump(mode="json", exclude_none=True)`; a placa ausente não é enviada.

### Estado e tela

- `moto_row` ganha `id_cliente` e `pode_vender` (`VENDEDOR`/`GERENTE`, com chassi, status `DISPONIVEL` ou `RESERVADA`).
- `open_venda` carrega os clientes ativos; numa unidade reservada, fixa o cliente da reserva. O valor vem preenchido com o preço da unidade.
- `build_venda_payload` valida cliente, valor (maior que zero, até duas casas) e placa antes de chamar o Xano.
- `confirm_venda` bloqueia operações simultâneas, chama o cliente, invalida o cache da vitrine, recarrega a lista e o detalhe aberto e mostra a notificação.
- O modal mostra o resumo da unidade (modelo, chassi, preço de tabela), cliente, valor, placa (opcional) e observação.

## Riscos

- **Índice único com nulos:** a unicidade de `placa` com valores nulos depende do Postgres do Xano tratar nulos como distintos. O teste de integração com escrita vende duas unidades sem placa para confirmar.
- **Plano Free:** o push publica na hora. Revisar o `--dry-run` antes.
