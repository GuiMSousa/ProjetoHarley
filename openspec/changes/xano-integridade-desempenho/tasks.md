# Tarefas — Change 16: integridade e desempenho do backend Xano

- [ ] Aprovação do escopo e das decisões de banco (itens 5 a 8 da proposta) pelo usuário.
- [x] `GET motos` com `join` e `eval`; teste estático de contrato (mesmos campos, sem consulta de tabela inteira). Feito em 2026-10-25 por causa de um HTTP 500 relatado em `/vendas` e na visão geral; falta o push.
- [x] Log `ERROR` dos 5xx com a `message` do Xano, para que o próximo 500 traga a causa: uma linha, mascaramento de e-mail, placa, chassi e sequências de 3+ dígitos, corte em 200 caracteres e corpo não JSON fora do log. Testes com mutação (as 6 variantes sem cada proteção falham).
- [x] Auditoria E2E de 2026-10-27, com o VENDEDOR de teste (A1): a `enforce_role` recusava com `throw`, e o Xano respondia HTTP 200 com `{payload, statement}`. Passa a recusar com `precondition` `accessdenied` (403), mantendo a exceção do `admin`. Contrato estático impede a volta do `throw` e exige cada ramo de perfil (ALL, GERENTE, VENDEDOR, MECANICO) com `accessdenied`; as 5 mutações são pegas. Falta o push.
- [x] Auditoria E2E (A2): `Vendas/detalhe_moto` com joins à esquerda (modelo, cliente e vendedor) numa só consulta; antes, toda unidade sem reserva respondia 400 "Missing param: field_value". Contrato estático sem `db.get` desses vínculos. Falta o push. Teste ao vivo de leitura (`test_seller_opens_the_detail_of_a_unit_without_a_reservation`) falha hoje com o 400 de produção e deve passar depois do push.
- [x] Auditoria E2E (M1 e B2): `SHOWROOM_FIELDS` da integração com `galeria`; miniatura da foto do modelo na tabela de `/vendas`.
- [ ] `POST entrada_mercadoria` com a baixa em ordem crescente de produto pelo banco; teste estático da ordem.
- [ ] `GET ordens_servico` com `output` restrito em `funcionarios`.
- [ ] Conferir a ordem de `Financeiro/resumo_operacoes` com uma sessão de gerente.
- [ ] Banco, conforme a decisão: `modelos_moto` (`galeria`, `default_motos`), índice único em `entrada_mercadoria` (depois de conferir duplicatas) e índice em `event_log.user_id`.
- [ ] Validador do MCP, `ruff`, `pytest` e `xano workspace push -d ./xano --dry-run` revisado; push com o OK do usuário.
- [ ] Docs: `docs/xano-api-client.md` e `docs/schema.sql`, se o banco mudar.
- [ ] Mover para o archive e commit (usuário).
