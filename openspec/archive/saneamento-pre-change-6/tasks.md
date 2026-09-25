# Tarefas

## Xano

- [x] Descartar `id_funcionario` em `PATCH transacoes/{id}` e `PATCH ordens_servico/{id}`.
- [x] Confirmar que `itens_ordem_servico` não possui `id_funcionario` (não aplicável).
- [x] Exigir `GERENTE` em `message/send_welcome_email` e restringir os campos lidos de `user`.
- [x] Bloquear `reset/request-reset-link` e `reset/magic-link-login`.
- [x] Remover o registro `user` completo do log de `reset/update_password`.
- [x] Negar funcionário inativo em `enforce_role`; expor `ativo` e remover o log por chamada em `auth/me`.
- [x] Endurecer `auth/signup`: sem token, credenciais obrigatórias, vínculo único com funcionário ativo.
- [x] Tornar `numero_documento` e `id_funcionario` de `entrada_mercadoria` anuláveis.
- [x] Criar `Estoque/normalizar_entradas_legadas`.
- [x] Validar todos os XanoScript (100 arquivos, 0 erros).

## Python

- [x] Separar a URL base do grupo `Authentication` (`XANO_AUTH_API_BASE_URL`).
- [x] Mapear `404` para `XanoNotFoundError`.
- [x] Confirmar `400`/`422` como `XanoValidationError` com mensagem legível.
- [x] Revisar DTOs: nenhum DTO de escrita envia `id_funcionario`, totais ou datas de autoria; valores financeiros com `> 0`.
- [x] Adicionar `ativo` a `XanoEmployee`.

## Reflex

- [x] Confirmar guard `ROUTE_ROLES` e `restore_session` no `on_load` de `/cadastros/*`, `/estoque/entradas`, `/admin` e `/workshop`.
- [x] Confirmar sidebar conforme a matriz (vendedor com leitura de produtos).
- [x] Centralizar mensagens em `feedback.py` e respostas em `AuthState._xano_error_response`.
- [x] Reiniciar estados das páginas ao encerrar a sessão.
- [x] Limpar linhas antigas em erro de carregamento.
- [x] Separar falha de recarga do resultado da gravação em cadastros.
- [x] Corrigir `StopIteration` em `open_edit`.

## Ambiente e testes

- [x] `env_file=".env"` no `rxconfig.py` e `python-dotenv>=1.1.0` em `requirements.txt`.
- [x] Atualizar `.env.example` com `XANO_AUTH_API_BASE_URL` e variáveis de teste.
- [x] Criar `tests/test_integration_xano.py` (ignorado sem Xano configurado).
- [x] Criar `tests/test_security_contracts.py` e ampliar testes de cliente, autenticação, cadastros e entradas.
- [ ] Executar a suíte de integração contra o Xano real (pendente: sem URL e credenciais neste workspace).

## Documentação e OpenSpec

- [x] `docs/xano-api-client.md`: grupos de API, deploy pela CLI, tabela de erros e testes.
- [x] `docs/domain-model.md`: usuários, funcionário ativo, legado de entradas e situação atual de motos, OS e transações.
- [x] `docs/project-structure.md`: passo de validação.
- [x] `openspec/specs/arquitetura-e-contratos.md`: novos requisitos.
- [x] Remover pastas vazias de `openspec/changes/`.
