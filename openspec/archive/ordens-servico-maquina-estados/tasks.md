# Tarefas

## 0. Decisões e preparação (antes do Apply)

- [x] Aprovar D1 — `id_mecanico` separado da autoria, restrito a `MECANICO` ativo.
- [x] Aprovar D2 — `id_cliente` como fotografia derivada da moto.
- [x] Aprovar D3 — `tipo_servico` e `descricao_problema` obrigatórios; `quilometragem` opcional.
- [x] Aprovar D4 — cancelamento a partir de `ABERTA` e `EM_ANDAMENTO`, com motivo.
- [x] Aprovar D5 — uma OS em aberto por moto.
- [x] Aprovar D6 — mutações de itens de OS bloqueadas até a Change 7.
- [x] Confirmar D7 — qualquer `GERENTE`/`MECANICO` transiciona qualquer OS.
- [x] Aprovar D8 — endpoint mínimo `GET oficina/mecanicos`.
- [x] Confirmar no validador XanoScript: `db.bulk.patch` **não** aceita `where` (substituído pelo índice único do histórico; ver notas na proposta); nomes resolvidos sem join duplo; input `enum` opcional validado.

## 1. Xano — schema

- [x] Adicionar a `ordens_servico` os campos anuláveis `id_cliente`, `id_mecanico`, `tipo_servico`, `descricao_problema`, `quilometragem`, `data_inicio`, `data_encerramento` e `motivo_cancelamento`.
- [x] Criar índices `id_cliente`, `id_mecanico` e `data_abertura desc`.
- [x] Criar a tabela `historico_status_os` com índices `id_os` e `created_at desc`.

## 2. Xano — funções

- [x] Criar `Oficina/validar_transicao_os` com a tabela de transições e a regra de motivo.
- [x] Criar `Oficina/detalhe_os` (OS enriquecida, histórico e itens).

## 3. Xano — endpoints

- [x] Reescrever `ordens_servico_POST.xs` (abertura transacional, D1, D2, D3, D5, histórico inicial).
- [x] Criar `ordens_servico/ordens_servico_id_status_POST.xs` (transição com compare-and-set e histórico).
- [x] Reescrever `ordens_servico_GET.xs` (enriquecido, filtros `status` e `id_moto_cliente`, ordenação).
- [x] Reescrever `ordens_servico/ordens_servico_id_GET.xs` usando `Oficina/detalhe_os`.
- [x] Criar `oficina/mecanicos_GET.xs`.
- [x] Bloquear `ordens_servico/ordens_servico_id_PUT.xs`, `_PATCH.xs` e `_DELETE.xs`.
- [x] Bloquear `itens_ordem_servico_POST.xs` e `itens_ordem_servico/itens_ordem_servico_id_PUT.xs`, `_PATCH.xs` e `_DELETE.xs`.
- [x] Validar todos os XanoScript.

## 4. Python — DTOs e cliente

- [x] Criar `Projeto_HarleyStore/services/ordens_servico.py` com `StatusOS`, `TipoServico`, `TRANSICOES_OS` e os DTOs de abertura, transição, resumo, histórico, item, detalhe e mecânico.
- [x] Adicionar `list_ordens_servico`, `get_ordem_servico`, `abrir_ordem_servico`, `transicionar_ordem_servico` e `list_mecanicos` ao `XanoClient`.

## 5. Reflex

- [x] `ROUTE_ROLES["/workshop"] = ALL_ROLES`; remover `AuthState.can_workshop` se ficar sem uso.
- [x] Criar `Projeto_HarleyStore/workshop_state.py` com as funções puras e `OficinaState`.
- [x] Implementar carga da lista com filtro por status, contagens, busca e paginação.
- [x] Implementar o detalhe com linha do tempo, itens somente leitura e histórico da moto.
- [x] Implementar a abertura (cliente → moto → mecânico, tipo, descrição e km) com validação local e bloqueio de reentrada.
- [x] Implementar as transições com confirmação, motivo de cancelamento e recarga após conflito.
- [x] Criar `Projeto_HarleyStore/workshop_pages.py` no tema Harley (badges, filtros, tabela e modais).
- [x] Registrar `/workshop` com `on_load=[AuthState.restore_session, WorkshopState.load_ordens]` e remover o placeholder.

## 6. Testes

- [x] Criar `tests/test_ordens_servico.py` (DTOs e cliente HTTP).
- [x] Criar `tests/test_workshop_state.py` (funções puras e eventos com a árvore real do Reflex).
- [x] Criar `tests/test_ordens_servico_contracts.py` (contratos XanoScript).
- [x] Atualizar `tests/test_authentication.py` (`/workshop` para os três perfis).
- [x] Atualizar `tests/test_hardening_contracts.py` e `tests/test_security_contracts.py` (PUT/PATCH de OS bloqueados; autoria no endpoint de transição).
- [x] Ampliar `tests/test_integration_xano.py` com cenários de leitura e de escrita de OS.

## 7. Documentação

- [x] `docs/domain-model.md`: campos novos da OS, `historico_status_os`, máquina de estados e regra de uma OS em aberto por moto.
- [x] `docs/xano-api-client.md`: DTOs, métodos, endpoints novos e bloqueados, matriz de acesso.

## 8. Verificação e Archive

- [x] `python -m unittest discover -s tests`.
- [x] `python -m py_compile` em todos os módulos.
- [x] `reflex compile --dry`.
- [x] Validador XanoScript em `xano/`.
- [ ] Publicar com `xano workspace push -d ./xano` (aditivo) e executar a suíte de integração com credenciais de perfil (pendente: fora do repositório).
- [x] Consolidar os requisitos em `openspec/specs/oficina-ordens-servico.md`.
- [x] Preencher "Resultado aplicado" e "Status" e mover a Change para `openspec/archive/`.

## Arquivos previstos

| Área | Criar | Alterar |
| --- | --- | --- |
| Xano — tabelas | `table/historico_status_os.xs` | `table/ordens_servico.xs` |
| Xano — funções | `function/oficina/validar_transicao_os.xs`, `function/oficina/detalhe_os.xs` | — |
| Xano — API | `api/harley/ordens_servico/ordens_servico_id_status_POST.xs`, `api/harley/oficina/mecanicos_GET.xs` | `ordens_servico_POST.xs`, `ordens_servico_GET.xs`, `ordens_servico/ordens_servico_id_{GET,PUT,PATCH,DELETE}.xs`, `itens_ordem_servico_POST.xs`, `itens_ordem_servico/itens_ordem_servico_id_{PUT,PATCH,DELETE}.xs` |
| Serviços | `services/ordens_servico.py` | `services/xano_client.py` |
| Reflex | `workshop_state.py`, `workshop_pages.py`, `formatting.py` | `auth.py`, `entradas_state.py`, `Projeto_HarleyStore.py` |
| Testes | `test_ordens_servico.py`, `test_workshop_state.py`, `test_ordens_servico_contracts.py` | `test_authentication.py`, `test_hardening_contracts.py`, `test_security_contracts.py`, `test_integration_xano.py` |
| Docs | — | `docs/domain-model.md`, `docs/xano-api-client.md` |

Nenhum arquivo de implementação deve ser alterado durante a etapa Propose.
