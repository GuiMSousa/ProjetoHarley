# Tarefas

## 0. Decisões

- [x] D1: placa opcional na venda e em `motos_clientes`, única quando informada (aprovado pelo usuário).
- [x] D2: valor mínimo de venda maior que zero, igual ao Xano; preço da unidade sugerido (aprovado pelo usuário).
- [x] D3 a D8: perfis, unidade reservada, estado final, nome do modelo, concorrência e cache da vitrine (proposta).

## 1. Xano

- [x] `table/motos_clientes.xs`: `text? placa? filters=trim`, mantendo o índice único.
- [x] `api/harley/vender_moto_POST.xs`: `text? placa? filters=trim|upper`.
- [x] `function/vendas/vender_moto.xs`:
  - placa vazia → nula; checagem de placa só quando informada; checagem de chassi separada;
  - nome do modelo comercial (`modelos_moto.nome_modelo`) na moto do cliente;
  - mensagens "Chassi já cadastrado…" e "Placa já cadastrada…".
- [x] Validar com o validador XanoScript e conferir os diagnósticos do VS Code.
- [x] `xano workspace push -d ./xano --dry-run`: só atualizações (`motos_clientes`, `Vendas/vender_moto`, `vender_moto POST` e a diferença pré-existente de `modelos_moto.destaque`).
- [ ] Publicar no Xano (usuário; plano Free publica na hora).

## 2. Cliente Python

- [x] `VendaMotoCreate` e `VendaMotoResultado` em `services/motos.py`.
- [x] `XanoClient.vender_moto` (`POST vender_moto`, `exclude_none`).
- [x] `MotoCliente*`: placa opcional; Cadastros trata placa em branco como ausente e mostra coluna vazia.

## 3. Tela `/vendas`

- [x] `moto_row`: `id_cliente` e `pode_vender`; regras `can_sell_unit` e `venda_ainda_possivel`.
- [x] `build_venda_payload` e `valor_inicial_venda`; mensagens de cliente, valor e placa.
- [x] Eventos `open_venda`, `close_venda`, `set_venda_*` e `confirm_venda`, com bloqueio de operações simultâneas.
- [x] Concorrência: recusa `400`/`404` recarrega a lista e fecha o modal se a unidade não é mais vendável.
- [x] Sucesso: `catalogo_cache.invalidate()` e recarga da lista.
- [x] Botão "Vender" (primário) nas linhas; "Reservar" passa a botão metálico; modal com resumo, cliente (fixo na reserva), valor, placa e observação.

## 4. Testes

- [x] `tests/test_venda_moto.py`: DTO e requisição do cliente (rota, token, corpo, placa omitida, erros tipados).
- [x] `tests/test_vendas_state.py`: regras, payload e fluxos (sucesso, reserva, formulário inválido, vendida por outro, placa duplicada, unidade removida, `403`, bloqueio).
- [x] `tests/test_cadastros*.py`: moto de cliente sem placa.
- [x] `tests/test_catalogo_vendas_contracts.py`: placa opcional, checagem condicional e nome do modelo.
- [x] `tests/test_integration_xano.py`: venda sem escrita, ciclo com escrita e corrida de duas vendas (ignorados sem credenciais).
- [x] Suíte offline, `py_compile` e `reflex compile --dry`.
- [ ] Integração real depois do push (`XANO_TEST_ALLOW_WRITES` e `XANO_TEST_CONCURRENCY`), confirmando que motos sem placa não colidem no índice único.

## 5. Documentação e arquivamento

- [x] `docs/domain-model.md` e `docs/xano-api-client.md` (contrato, matriz, checklist de deploy, testes).
- [ ] Arquivar: aplicar o delta em `openspec/specs/catalogo-vendas-motos.md` e mover a change para `openspec/archive/` depois do push e da integração.
