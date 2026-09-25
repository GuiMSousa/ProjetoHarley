# Design: saneamento e hardening pré-Change 6

## Grupos de API

`xano_config.xano_auth_api_base_url()` lê `XANO_AUTH_API_BASE_URL` e recorre a `XANO_API_BASE_URL` se ausente. `XanoClient.request` aceita `base_url`; com ele, o caminho é resolvido como URL absoluta, que o `httpx` usa no lugar da `base_url` do cliente. `login` e `current_user` passam `self._auth_base_url`. Nenhum outro método mudou de grupo.

## Identidade

- `enforce_role` lê `ativo` do funcionário e nega com `accessdenied` quando `ativo == false`. Registros legados com `ativo` nulo continuam ativos (`!= false`).
- `auth/me` inclui `ativo` e deixou de chamar `log_event`.
- `XanoEmployee.ativo` tem padrão `True`; `AuthState._load_user` recusa funcionário inativo com mensagem própria.
- `auth/signup` valida funcionário existente e ativo e ausência de usuário vinculado, exige email e senha e responde `{user_id, id_funcionario}`.

## Superfície pública

Somente `auth/login` fica sem `auth = "user"` e sem bloqueio. Endpoints de recuperação foram reescritos para `precondition (false)` com `accessdenied`, preservando rota e `guid` para que o push atualize os objetos existentes em vez de criar novos.

## Autoria em PATCH

`data = $input|pick:($raw_input|keys)|unset:"id_funcionario"|...`, o mesmo padrão usado para `estoque_qtd` em produtos na Change 5. `itens_ordem_servico` não possui a coluna, portanto não precisou de ajuste.

## Registros legados de entrada

Conforme a documentação XanoScript, `text x?` é opcional e **não anulável**, e `text? x?` é opcional e anulável. Com o campo anulável, registros legados ficam `null` e não colidem no índice único. Como o push parcial não relaxa restrições, a publicação exige `--sync`. A função idempotente `Estoque/normalizar_entradas_legadas` converte `null`/`""` em `LEGADO-<id>`.

## Tratamento de erros na UI

- `feedback.error_feedback(error)` é a única tradução de exceções para mensagens.
- `AuthState._xano_error_response(error)`: `401` limpa a sessão, reinicia os estados das páginas e redireciona para `/login`; os demais erros geram toast.
- `AuthState._clear_session` percorre os substates carregados a partir do `AuthState` e chama `reset()`. O `reset()` de um substate só reinicia variáveis próprias, não as herdadas da sessão.
- `CadastrosState._refresh_after_mutation` isola a recarga pós-gravação; `_clear_section_rows` impede exibir linhas antigas junto de um erro.

## Testes de integração

`tests/test_integration_xano.py` lê o `.env` com um parser mínimo (sem dependência nova nos testes) e o ambiente, que tem precedência. As classes são ignoradas sem `XANO_API_BASE_URL` real. Os cenários de escrita exigem `XANO_TEST_ALLOW_WRITES=true`, porque entradas são imutáveis e ficam na base.
