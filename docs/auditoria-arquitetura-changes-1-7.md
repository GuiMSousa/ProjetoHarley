# Relatório de auditoria: arquitetura do HarleyStore (após as Changes 1 a 7)

- **Data:** 2026-09-25
- **Escopo:** código Python e Reflex, exports do Xano (`xano/`), testes e documentação, após a publicação da Change 7.
- **Natureza:** auditoria somente de leitura; nenhum arquivo foi alterado durante a análise. O acompanhamento das correções está no anexo ao final.

**Estado geral: saudável, com ressalvas. Nota 8/10.**

O código compila, os testes passam e as regras de negócio vivem no Xano, que é quem decide. Há três ressalvas:

- As garantias de concorrência das Changes 5 a 7 **nunca foram testadas contra o Xano real**.
- O módulo de transações ainda é um CRUD genérico.
- Há endpoints de exclusão física expostos que a interface não usa.

## 1. Verificações automáticas

| Verificação | Resultado |
|---|---|
| `unittest discover -s tests` | 190 testes: 164 aprovados, 26 de integração ignorados |
| `py_compile` | 36 módulos OK |
| `reflex compile --dry` | compilou sem erros |
| Validador XanoScript | 110 arquivos, 0 erros |
| Change 7 no Xano | publicada: os 5 `.xs` modificados só têm os guids gravados pelo push, ainda sem commit |

**Os 26 testes ignorados são o ponto cego.** O `.env` tem os endereços do Xano, mas nenhuma credencial `XANO_TEST_*`. Por isso, só `test_public_surface_is_closed` roda contra o Xano real.

## 2. Segurança e controle de acesso

**Está bem:**

- Os 81 endpoints foram mapeados.
- Todas as rotas de negócio exigem `auth = "user"` e chamam `enforce_role`.
- Só `auth/login` é público; o fluxo de recuperação por magic link continua bloqueado com 403.
- As alterações genéricas de OS, itens, entradas e itens de compra respondem 403.
- `funcionarios` e `fornecedores` são exclusivos do GERENTE.
- A autoria vem sempre do JWT (`$auth.id → user.id_funcionario`).
- No Reflex, todas as páginas protegidas usam `guarded_page` e restauram a sessão no `on_load`. O `ROUTE_ROLES` corresponde à matriz de permissões.
- Não há segredos no export do Xano, e a função `seed_gerente` não é chamada por nenhum endpoint.

**Problemas encontrados:**

- **`DELETE` físico ativo em 7 recursos:** clientes, motos de clientes, produtos, fornecedores, funcionários, motos da loja e transações, todos só para GERENTE.
  - A interface nunca os usa: a desativação é feita por `PATCH` com `ativo = false`.
  - Nenhum desses endpoints verifica se o registro tem vínculos. Apagar um produto deixa órfãos o livro de estoque, os itens de OS e as entradas.
- **`transacoes` continua um CRUD genérico:**
  - O VENDEDOR pode fazer `PUT`/`PATCH` de qualquer transação, incluindo `valor_total`, `tipo_transacao` e a data, que vem do payload.
  - O `GET` está aberto a todos os perfis e o `DELETE` é físico.
- **`reset/update_password`:**
  - Troca a senha sem pedir a senha atual e não chama `enforce_role`: um funcionário desativado com token ainda válido consegue trocá-la.
  - Os dois campos são opcionais. Se ambos vierem vazios, a verificação `null == null` passa. O que o Xano grava nesse caso não foi verificado.
  - Com um token roubado, alguém fica com a conta de forma permanente.
- **`GET clientes`** entrega CPF/CNPJ, email e endereço a todos os perfis, incluindo o mecânico. É uma questão de minimização de dados (LGPD).
- **Token do Swagger** do grupo HARLEY está versionado em `xano/api/harley/harley.xs`, e o repositório está no GitHub. Dá acesso à documentação da API, não aos dados.

## 3. Concorrência e integridade dos dados

| Mecanismo | Estado |
|---|---|
| `historico_status_os`: índice único `(id_os, status_anterior)` com `try_catch` | correto |
| `movimentacoes_estoque`: índice único `(id_produto, versao_anterior)` via `Estoque/movimentar_estoque`, único ponto que escreve o saldo (garantido por teste) | correto |
| Itens de OS: bloqueio da OS antes de reler o status, com `try_catch` | correto; o teste de repetição de produto fica seguro por esse bloqueio |
| Cancelamento da OS com devolução das peças | correto: a devolução vem depois do `patch`, em ordem de produto |
| **Entrada de mercadoria** | **sem `try_catch`**: numa corrida devolve 500, e a interface mostra "Não foi possível comunicar com o Xano". Não grava nada, mas a mensagem engana |
| "Uma OS em aberto por moto" | só há verificação prévia, sem bloqueio: duas aberturas simultâneas podem criar duas OS (probabilidade baixa) |

**Esquemas:**

- **Produtos com saldo nulo:** `produtos.estoque_qtd` aceita nulo no Xano, mas o DTO `Produto` exige um inteiro. Confirmei que um único produto com saldo nulo faz o `list_produtos` falhar por inteiro. Isso quebra o cadastro de produtos, o catálogo da oficina e a entrada.
- **Índices únicos sem normalização:** placa, chassi, `cpf_cnpj` e `produtos.codigo` só passam por `trim`. `abc1d23` e `ABC1D23`, ou um CPF com e sem pontuação, entram como duplicados.
- **Vínculo usuário–funcionário:** `user.id_funcionario` não tem índice único. A regra "um usuário por funcionário" depende só da verificação no `signup`.
- **`motos` (estoque da loja):** não tem preço, chassi, status nem `ativo`, e o `DELETE` é físico. Já estava documentado como pendente.

## 4. Código e testes

**Código morto:**

- `AuthState.can_manage` não é usado.
- `XanoClient.list_moto`, `create_moto`, `update_moto` e `delete_moto` não têm interface nem testes, e `delete_moto` usa o `DELETE` físico.
- `styles/theme.global_theme` duplica `theme_config`.
- Sobras do quick-start do Xano: `ai/agent/xano_example_agent` e `ai/tool/search_xano_docs`.

**Duplicação e acoplamento:**

- `labeled` e `error_callout` estão copiados em `entradas_pages.py` e `workshop_pages.py`.
- `_validation_text` (entradas) e `_first_error` (oficina) têm a mesma estrutura.
- `operation_is_blocked` vive em `cadastros_state.py` e é importado pelas entradas e pela oficina, o que acopla páginas entre si.
- Há 26 chamadas `rx.toast(..., position="top-right")` repetidas, sem uma função comum em `feedback.py`.

**Consolidação:**

- `formatting.py` e `feedback.py` são usados pelas entradas, pela oficina e pelo `AuthState`.
- Os cadastros ainda não usam `formatting.py`: mostram o preço cru (`45.9` em vez de `R$ 45,90`).
- O dashboard tem uma cor fixa (`#a7a7a7`) fora do tema.

**Tamanho:** `workshop_state.py` tem 994 linhas e `workshop_pages.py` tem 766.

**Testes:**

- Cobrem bem os DTOs, o cliente, as regras puras, os eventos e os contratos XanoScript.
- As páginas só são verificadas pela compilação.
- Não há ferramenta de cobertura nem linter instalados no ambiente.

## 5. Débitos técnicos por prioridade

| # | Prioridade | Débito |
|---|---|---|
| 1 | Alta | Rodar a integração com escrita e concorrência contra o Xano real (credenciais `XANO_TEST_*`, `ALLOW_WRITES`, `CONCURRENCY`) |
| 2 | Alta | Bloquear com 403 os 7 `DELETE` físicos, com o mesmo padrão já usado para as entradas |
| 3 | Alta (antes de Vendas) | Redesenhar `transacoes`: imutável, valores calculados no servidor, sem `PUT`/`PATCH` livres |
| 4 | Média | `reset/update_password`: exigir a senha atual, campos obrigatórios e `enforce_role` |
| 5 | Média | Aceitar saldo nulo no DTO `Produto` (tratar como 0) ou dar ao esquema um valor padrão |
| 6 | Média | `try_catch` na entrada de mercadoria, com mensagem de conflito |
| 7 | Média | Normalizar placa, chassi, CPF/CNPJ e código antes dos índices únicos (o chassi será essencial nas vendas) |
| 8 | Baixa | Remover o código morto e juntar `labeled`, `error_callout`, `operation_is_blocked` e os toasts em módulos comuns |
| 9 | Baixa | Dividir `workshop_state.py` e `workshop_pages.py` (por exemplo, separar os itens) |
| 10 | Baixa | Índice único em `user.id_funcionario`; trocar o token do Swagger; reduzir os dados de clientes expostos ao mecânico |
| 11 | Baixa | `/admin` é só um marcador: a criação de usuários ainda não tem interface |

## 6. Prontidão para as próximas fases

- **Redesign visual (UI/UX): pronto.** A lógica está em funções puras testadas e separadas dos componentes, e as cores já estão centralizadas em `styles/theme.py`.
  - Recomendo fazer antes os itens 8 e 9: o redesign vai mexer exatamente nos helpers duplicados e nos arquivos grandes.
- **Catálogo e vendas de motos: pronto com condições.**
  - A fundação serve de base: livro de estoque, padrão transacional com bloqueio e controle de permissões por endpoint.
  - Antes de começar, convém fechar os itens 1 e 2.
  - Os itens 3 e 7 e o modelo de `motos` devem fazer parte da própria proposta de vendas.

---

## Anexo: acompanhamento

### Sprint de saneamento pós-Change 7 (2026-09-25)

Registro OpenSpec em `openspec/archive/saneamento-pos-change-7/`.

| # | Débito | Situação |
|---|---|---|
| 1 | Integração com escrita e concorrência no Xano real | **Pendente** (depende de credenciais de teste e do push) |
| 2 | `DELETE` físico nos 7 recursos | **Resolvido** no código: `403` com rota e guid preservados; aguarda push |
| 3 | Redesenho de `transacoes` | Pendente (Change de vendas) |
| 4 | `reset/update_password` | **Resolvido** no código: senha atual, campos obrigatórios, `enforce_role` e sem `trim`; aguarda push |
| 5 | Saldo nulo no DTO `Produto` | **Resolvido** |
| 6 | `try_catch` na entrada de mercadoria | Pendente |
| 7 | Normalização antes dos índices únicos | Pendente |
| 8 | Código morto e helpers comuns | **Resolvido em parte**: `can_manage`, `global_theme`, `delete_moto` e o agente e a ferramenta de exemplo removidos; `labeled`, `error_callout` e `operation_is_blocked` em `ui_helpers.py`, e os 26 toasts via `toast_error`/`toast_success` em `feedback.py`. Continuam pendentes `list_motos`, `create_moto` e `update_moto` (serão revistos na Change de catálogo), a unificação de `_validation_text`/`_first_error`, o preço cru nos cadastros e a cor fixa do dashboard |
| 9 | Divisão dos arquivos da oficina | Pendente |
| 10 | Índice em `user.id_funcionario`, token do Swagger, dados de clientes | Pendente |
| 11 | Tela de administração | Pendente |

**Novo achado durante a sprint:** o workspace do Xano limita a taxa de requisições. Depois de cerca de 6 chamadas seguidas, responde `429`. O `XanoClient` trata esse código como erro genérico, e a interface mostra "Não foi possível comunicar com o Xano". A suíte de integração completa, com credenciais configuradas, vai atingir esse limite e falhar de forma intermitente, o que já acontece hoje com `test_public_surface_is_closed` quando a suíte roda várias vezes seguidas. Recomenda-se, antes de executar o item 1:

- um erro tipado para `429`, com mensagem "Muitas requisições, aguarde alguns segundos";
- nova tentativa com espera (backoff) nos testes de integração.
