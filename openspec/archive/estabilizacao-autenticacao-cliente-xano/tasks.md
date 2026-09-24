# Tarefas

## Preparação e contrato

- [x] Confirmar os endpoints Xano de login e `auth/me` e registrar o payload real observado.
- [x] Confirmar que o endpoint de signup não será exposto pela aplicação e documentar o fluxo administrativo futuro.
- [x] Definir os modelos mínimos de resposta para token, usuário e funcionário sem incluir credenciais sensíveis.

## Cliente Xano

- [x] Refatorar `Projeto_HarleyStore/services/xano_client.py` para manter uma operação HTTP genérica reutilizável pelos endpoints de negócio.
- [x] Preservar os métodos auxiliares HTTP como delegações consistentes à operação genérica.
- [x] Implementar validação explícita do retorno de `login` e `current_user`.
- [x] Garantir tratamento tipado e mensagens seguras para `401`, `403`, `422`, outros status e falhas de transporte.
- [x] Confirmar que nenhum token, senha ou hash seja registrado ou incluído em exceções.

## Reflex e sessão

- [x] Corrigir `AuthState.login` para redirecionar somente após `load_user` validar a sessão.
- [x] Garantir que falha de `load_user` limpe a sessão e mantenha o usuário na autenticação.
- [x] Tornar o atributo `secure` do cookie configurável por `XANO_AUTH_COOKIE_SECURE`.
- [x] Definir conversão segura de valores booleanos da configuração de ambiente.
- [x] Melhorar as mensagens visuais para credenciais inválidas, sessão expirada, falta de permissão e indisponibilidade do Xano.
- [x] Remover ou impedir qualquer rota, link ou ação de signup público.

## Testes e verificação

- [x] Criar testes do cliente HTTP usando transporte simulado.
- [x] Criar testes de contrato para login e `auth/me`.
- [x] Criar testes do `AuthState` para login válido, `401`, `403`, usuário sem funcionário e falha de transporte.
- [x] Testar a configuração do cookie em ambiente local e de produção.
- [x] Executar `python -m py_compile` nos arquivos Python afetados.
- [x] Executar `reflex compile --dry`.
- [x] Executar validação XanoScript dos arquivos alterados, incluindo `enforce_role`.
- [x] Registrar resultados, limitações de ambiente e decisões tomadas antes do Archive.
- [x] Registrar que o teste de integração contra Xano real depende de `XANO_API_BASE_URL` e credenciais não disponíveis neste ambiente.

## Arquivos previstos

- `Projeto_HarleyStore/services/xano_client.py`
- `Projeto_HarleyStore/auth.py`
- `Projeto_HarleyStore/components.py`
- `Projeto_HarleyStore/xano_config.py` ou novo módulo de configuração de sessão
- testes novos para cliente e autenticação
- documentação de integração Xano, se o payload real exigir atualização

Nenhum arquivo de implementação deve ser alterado durante a etapa Propose.
