# Proposta: saneamento pós-Change 7

## Contexto

A auditoria de arquitetura feita após a Change 7 (`docs/auditoria-arquitetura-changes-1-7.md`) listou 11 débitos técnicos. Esta sprint trata os itens de segurança e resiliência de maior prioridade e a consolidação de helpers de interface, antes do redesign visual e do catálogo de motos.

## Problemas tratados

1. **`DELETE` físico exposto** em clientes, motos de clientes, produtos, fornecedores, funcionários, motos da loja e transações. A interface já desativa por `PATCH` com `ativo = false`, e os endpoints não verificavam vínculos: apagar um produto deixaria órfãos o livro de estoque, os itens de OS e as entradas.
2. **`reset/update_password` fraco:** trocava a senha sem pedir a atual, não chamava `enforce_role`, tinha os dois campos opcionais e aplicava `trim`, diferentemente de `auth/login` e `auth/signup`. Um token vazado permitia tomar a conta de forma permanente.
3. **Saldo nulo:** um produto com `estoque_qtd` nulo no Xano fazia `list_produtos` falhar por inteiro, quebrando o cadastro, o catálogo da oficina e a entrada de mercadoria.
4. **Duplicação e acoplamento na interface:**
   - `labeled` e `error_callout` estavam copiados em `entradas_pages.py` e `workshop_pages.py`, e `cadastros_pages.py` repetia os mesmos padrões inline;
   - `operation_is_blocked` vivia em `cadastros_state.py` e era importado pelas outras páginas;
   - havia 26 chamadas `rx.toast(..., position="top-right")` repetidas.
5. **Código morto:** `AuthState.can_manage`, `styles/theme.global_theme` (duplicava `theme_config`), `XanoClient.delete_moto` (chamaria o `DELETE` agora bloqueado), e o agente e a ferramenta de exemplo de IA do quick-start do Xano.

## Decisões

- **Bloqueio com rota preservada:** os 7 `DELETE` mantêm rota, input e guid, passam por `enforce_role` `GERENTE` e respondem `precondition (false)` `accessdenied`, o mesmo padrão das entradas imutáveis. Para as motos da loja e as transações, que ainda não têm `ativo`, a mensagem remete às Changes de catálogo e de vendas.
- **Troca de senha:**
  - `current_password`, `password` (mínimo de 8 caracteres) e `confirm_password` são obrigatórios;
  - o endpoint chama `enforce_role` `ALL` (funcionário vinculado ativo) e confere a senha atual com `security.check_password` antes de gravar;
  - a nova senha deve diferir da atual, e nenhuma senha passa por `trim`;
  - erros de negócio respondem `400` com mensagem em português, e o log guarda apenas o id.
- **Saldo nulo:** só o modelo de leitura `Produto` converte `estoque_qtd` nulo em `0`, a mesma leitura de `Estoque/movimentar_estoque`. `ProdutoCreate` continua exigindo um saldo válido.
- **Módulos compartilhados:**
  - `ui_helpers.py` reúne `labeled`, `error_callout` e `operation_is_blocked`, a trava de reentrada usada pelos eventos das páginas;
  - `feedback.py` ganha `toast_error` e `toast_success`, com posição única (`TOAST_POSITION`).

## Fora do escopo

- Redesenho de `transacoes` (Change de vendas).
- `try_catch` na entrada de mercadoria.
- Normalização de placa, chassi, CPF/CNPJ e código.
- Divisão dos arquivos da oficina.
- `list_motos`, `create_moto` e `update_moto`, que serão revistos na Change de catálogo.
- Unificação de `_validation_text` e `_first_error`, preço formatado nos cadastros e cor fixa do dashboard.
- Tela de troca de senha e método correspondente no `XanoClient`.
- Execução da integração contra o Xano real.

## Resultado aplicado

- **Xano:**
  - 7 `DELETE` bloqueados;
  - `reset/update_password` reescrito;
  - `xano/ai/agent/xano_example_agent.xs` e `xano/ai/tool/search_xano_docs.xs` removidos (nenhum endpoint os referenciava).
- **Python e Reflex:**
  - validador de saldo nulo em `Produto`;
  - `ui_helpers.py` novo;
  - toasts centralizados em `feedback.py`;
  - páginas de entradas, oficina e cadastros usando os helpers comuns;
  - código morto removido.
- **Testes:**
  - novos contratos para os `DELETE` bloqueados;
  - a única exclusão física do sistema passa a ser a remoção de item de OS;
  - contrato da troca de senha;
  - saldo nulo;
  - novo `tests/test_ui_helpers.py`, que também impede novas cópias dos helpers e chamadas diretas a `rx.toast`;
  - dois cenários de integração, seguros antes e depois do push: `DELETE` com id inexistente e troca de senha que reenvia a própria senha atual.
- **Documentação:**
  - `docs/auditoria-arquitetura-changes-1-7.md` (relatório e acompanhamento);
  - `docs/domain-model.md`, `docs/xano-api-client.md` e `openspec/specs/arquitetura-e-contratos.md` atualizados.

### Notas de implementação

- A remoção local dos arquivos de IA não os apaga do workspace num push comum. Para removê-los do Xano, é preciso `xano workspace push -d ./xano --sync --delete`, revisando antes o `--dry-run`, ou apagá-los pelo painel.
- `cadastros_pages.py` também passou a usar `labeled` e `error_callout`: repetia inline os mesmos componentes, embora não constasse da auditoria.
- **Novo achado:** o workspace do Xano responde `429` depois de cerca de 6 requisições seguidas. `test_public_surface_is_closed` falhou de forma intermitente por isso quando a suíte rodou várias vezes em sequência (confirmado com uma sonda: seis `403` seguidos de `429`). Não é uma regressão, mas afeta a execução da integração com credenciais. O registro e a recomendação estão no anexo do relatório de auditoria.

## Status

Aplicada e verificada em 2026-09-25.

- `python -m unittest discover -s tests`: 199 testes, com 171 executados e aprovados e 28 de integração ignorados por falta de credenciais de perfil e das flags de escrita.
- `python -m py_compile`: 38 módulos, OK.
- `reflex compile --dry`: OK.
- Validador XanoScript: 108 arquivos, 0 erros.

Pendente fora do repositório:

- `xano workspace push -d ./xano` (as mudanças de endpoint são atualizações; `--sync --delete` só se quiser remover o agente e a ferramenta de exemplo do workspace);
- rodar a integração com as credenciais `XANO_TEST_*`.
