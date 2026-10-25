# Proposta: saneamento e hardening pré-Change 6

## Contexto

Antes de iniciar as ordens de serviço, foi solicitada uma auditoria completa do repositório (Xano, Python e Reflex) para fechar brechas de segurança, alinhar schemas e endpoints e preparar testes de integração contra um Xano real. Nenhuma das Changes 1 a 5 havia sido executada contra o backend real.

## Problemas encontrados

### Críticos

1. **Grupos de API com URLs diferentes.** `auth/login` e `auth/me` pertencem ao grupo `Authentication` (`api:mN0Sp2sG`), e os endpoints de negócio ao grupo `HARLEY` (`api:AwslAPW3`), mas o `XanoClient` usava uma única `XANO_API_BASE_URL`. Com qualquer valor, o login ou os endpoints de negócio respondiam `404`.
2. **`auth/signup` devolvia o JWT do usuário criado ao gerente**, permitindo agir em nome de vendedores e mecânicos e anulando a autoria derivada do JWT.
3. **Autoria forjável em `PATCH`.** `PATCH transacoes/{id}` e `PATCH ordens_servico/{id}` gravavam `id_funcionario` vindo do payload.
4. **Funcionário desativado mantinha acesso.** `enforce_role` e `auth/me` ignoravam `funcionarios.ativo`.

### Altos

5. `message/send_welcome_email` era público e permitia disparar emails para qualquer `user_id`.
6. `reset/request-reset-link` e `reset/magic-link-login` estavam públicos sem uso nem homologação.
7. `reset/update_password` gravava o registro `user` completo, com hash da senha, em `event_log.metadata`.
8. `entrada_mercadoria.numero_documento` estava declarado como opcional e não anulável (`text numero_documento?`). Registros legados recebem `""` e colidem no índice único `(id_fornecedor, numero_documento)`.

### Médios

9. `auth/me` gravava um log a cada chamada, o que desde a Change 5 ocorre a cada navegação.
10. `auth/signup` aceitava email e senha ausentes, funcionário inativo ou já vinculado, e respondia email duplicado como `403`.
11. `404` virava erro genérico e a UI dizia "falha de comunicação".
12. Os cadastros exibiam mensagens de erro em inglês, não tratavam sessão expirada e mantinham linhas antigas visíveis ao lado de um erro de carregamento.
13. Em `save_form` e `deactivate`, uma falha ao recarregar a lista era reportada como falha da gravação já concluída.
14. `open_edit` de moto de cliente lançava `StopIteration` quando o cliente não estava carregado.
15. Logout e sessão expirada não limpavam listas e formulários carregados pelas páginas.
16. O `.env` descrito em `.env.example` nunca era carregado: faltavam `env_file` no `rxconfig.py` e o pacote `python-dotenv`.
17. Havia duas pastas vazias em `openspec/changes/` duplicando nomes já arquivados.

## Objetivo

Corrigir os problemas acima sem introduzir regras de OS, vendas ou estoque, e deixar a suíte pronta para validar o backend real.

## Fora do escopo

- Regras de status de OS, itens de OS e baixa de estoque (Changes 7 e 8).
- Bloqueio dos `DELETE` físicos de cadastros, OS e transações (decisão de negócio pendente).
- Modelagem de venda de peças e de motos.
- Troca de senha autenticada com confirmação da senha atual.
- Handlers Reflex assíncronos.

## Resultado aplicado

- `XANO_AUTH_API_BASE_URL` e `request(..., base_url=...)`; login e `auth/me` usam o grupo `Authentication`.
- `auth/signup` sem emissão de token, com email e senha obrigatórios, funcionário existente, ativo e ainda sem usuário, e email duplicado como `400`.
- `PATCH` de OS e transações descartam `id_funcionario`.
- `enforce_role` nega funcionário inativo; `auth/me` devolve `ativo` e deixou de gravar log por chamada; o Reflex recusa a sessão de funcionário inativo.
- `send_welcome_email` exige `GERENTE` e lê apenas id, nome e email; `request-reset-link` e `magic-link-login` bloqueados.
- `update_password` registra apenas o id do usuário.
- `numero_documento` e `id_funcionario` de `entrada_mercadoria` anuláveis, com a função `Estoque/normalizar_entradas_legadas`.
- `XanoNotFoundError` para `404`; mensagens da UI centralizadas em `feedback.error_feedback`, e tratamento uniforme em `AuthState._xano_error_response`.
- Cadastros com mensagens em português, sessão expirada levando ao login, linhas limpas em erro, recarga pós-gravação separada e `open_edit` sem `StopIteration`.
- Sessão encerrada ou expirada reinicia os estados das páginas.
- `env_file=".env"` no `rxconfig.py` e `python-dotenv>=1.1.0` em `requirements.txt`.
- Suíte de integração `tests/test_integration_xano.py`, ignorada sem Xano configurado.
- Documentação de deploy (`xano workspace push -d ./xano`), grupos de API, erros e testes.
- Pastas vazias removidas de `openspec/changes/`.

## Status

Aplicada, verificada e arquivada em 2026-09-24.

- `python -m unittest discover -s tests`: 100 testes, 92 executados e aprovados, 8 de integração ignorados por falta de Xano configurado.
- `python -m py_compile`: 29 módulos, OK.
- `reflex compile --dry`: OK.
- Validador XanoScript (`@xano/developer-mcp`): 100 arquivos, 0 erros.

A suíte de integração não foi executada contra o Xano real por falta de URL e credenciais neste workspace.
