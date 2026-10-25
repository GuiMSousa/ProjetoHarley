# Tarefas

## 1. Relatório

- [x] Salvar o relatório de auditoria em `docs/auditoria-arquitetura-changes-1-7.md`, com anexo de acompanhamento.

## 2. Segurança (Xano)

- [x] Bloquear com `403` o `DELETE` de `clientes`, `motos_clientes`, `produtos`, `fornecedores`, `funcionarios`, `motos` e `transacoes`, preservando rota, input e guid.
- [x] Reescrever `reset/update_password`:
  - [x] campos obrigatórios `current_password`, `password` e `confirm_password`;
  - [x] `enforce_role` `ALL`;
  - [x] `security.check_password` antes da gravação;
  - [x] nova senha diferente da atual;
  - [x] sem `trim`.
- [x] Remover o agente e a ferramenta de exemplo de IA do quick-start.
- [x] Validar os XanoScript.

## 3. Resiliência (Python)

- [x] `Produto` lê `estoque_qtd` nulo como `0`; `ProdutoCreate` continua estrito.

## 4. Interface (Reflex)

- [x] Criar `ui_helpers.py` com `labeled`, `error_callout` e `operation_is_blocked`.
- [x] Remover as cópias de `entradas_pages.py` e `workshop_pages.py` e usar os helpers em `cadastros_pages.py`.
- [x] Mover `operation_is_blocked` de `cadastros_state.py` e atualizar os imports dos três estados.
- [x] Criar `toast_error` e `toast_success` em `feedback.py` e substituir as 26 chamadas a `rx.toast`.
- [x] Remover `AuthState.can_manage`, `styles/theme.global_theme` e `XanoClient.delete_moto`.

## 5. Testes

- [x] Contratos: `DELETE` bloqueados, única exclusão física (itens de OS), troca de senha.
- [x] `Produto` com saldo nulo.
- [x] `tests/test_ui_helpers.py`: trava de reentrada, toasts, componentes e ausência de cópias ou `rx.toast` direto.
- [x] Integração: `DELETE` bloqueados e troca de senha sem a senha atual (cenários seguros antes do push).

## 6. Verificação e documentação

- [x] `unittest`, `py_compile`, `reflex compile --dry` e validador XanoScript.
- [x] Atualizar `docs/domain-model.md`, `docs/xano-api-client.md` e `openspec/specs/arquitetura-e-contratos.md`.

## Fora do repositório (usuário)

- [ ] `xano workspace push -d ./xano` (e `--sync --delete`, após o `--dry-run`, para remover do workspace o agente e a ferramenta de exemplo).
- [ ] Integração com `XANO_TEST_*`.
