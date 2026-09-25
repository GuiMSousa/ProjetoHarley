# Cliente HTTP do Xano

O Reflex acessa o backend somente através de `Projeto_HarleyStore.services.xano_client.XanoClient`.

## Configuração

Cada grupo de APIs do Xano tem a própria URL base (`https://<instância>/api:<canonical>`). O workspace usa dois grupos:

| Variável | Grupo Xano | Canonical no export | Endpoints |
| --- | --- | --- | --- |
| `XANO_API_BASE_URL` | `HARLEY` | `AwslAPW3` (`xano/api/harley/harley.xs`) | cadastros, entradas, OS, transações |
| `XANO_AUTH_API_BASE_URL` | `Authentication` | `mN0Sp2sG` (`xano/api/authentication/authentication.xs`) | `auth/login`, `auth/me` |

`XANO_AUTH_API_BASE_URL` recorre a `XANO_API_BASE_URL` quando omitida. Sem a variável própria, porém, o login falha com `404` sempre que os grupos forem diferentes, como neste workspace.

As variáveis podem vir do ambiente ou de um arquivo `.env` na raiz: `rxconfig.py` declara `env_file=".env"` e o carregamento usa `python-dotenv`. O `.env` está no `.gitignore`; `.env.example` mostra o formato. `XANO_AUTH_COOKIE_SECURE` deve ser `true` quando a aplicação for servida por HTTPS.

## Publicação do backend (deploy)

Os arquivos em `xano/` são a fonte versionada do workspace e são publicados pela CLI do Xano:

```bash
xano auth                              # uma vez: cria o perfil com instância e workspace
xano workspace push -d ./xano --dry-run    # pré-visualiza as alterações
xano workspace push -d ./xano              # publica somente o que mudou
```

Regras importantes:

- O push padrão é parcial e aditivo: adiciona e atualiza, mas **não remove nem relaxa restrições**. Tornar um campo anulável (por exemplo, `entrada_mercadoria.numero_documento`) ou remover colunas exige `xano workspace push -d ./xano --sync`.
- `--sync --delete` também remove do workspace objetos ausentes em `xano/`; use apenas depois de revisar o `--dry-run`.
- Para testar antes de publicar no live, use um branch: `xano workspace push -d ./xano -b <branch>`.
- O push grava de volta os `guid` atribuídos pelo servidor; faça commit desses arquivos.
- Valide os arquivos antes do push com o validador do `@xano/developer-mcp` (configurado em `.vscode/mcp.json`).

### Checklist pós-deploy da Change 5 e do saneamento

1. Publicar com `--sync` (o schema de `entrada_mercadoria` relaxou `numero_documento` e `id_funcionario` para anuláveis).
2. Executar uma vez a função `Estoque/normalizar_entradas_legadas`: entradas antigas sem documento passam a `LEGADO-<id>`.
3. Conferir que não há produtos antigos com `codigo` vazio repetido; o índice único de `produtos.codigo` falharia na criação.
4. Rodar a suíte de integração (seção "Testes de integração").

## Autenticação

A instância autenticada recebe o JWT através do argumento `token`. O cliente envia o cabeçalho:

```text
Authorization: Bearer <JWT>
```

O cliente não persiste tokens, não os registra em logs e não os envia em query strings. O Reflex guarda o JWT no cookie `harley_auth_token` e restaura a sessão com `auth/me` no `on_load` de cada rota protegida.

`auth/me` devolve `{user, funcionario}`. `XanoEmployee.ativo` indica se o funcionário vinculado está ativo; o Reflex recusa a sessão de funcionário inativo, e o Xano (`enforce_role`) nega qualquer operação de negócio a ele.

Somente `auth/login` é público. `auth/signup` exige `GERENTE`, cria o usuário vinculado a um funcionário ativo e ainda sem usuário, e **não** devolve token do novo usuário. `message/send_welcome_email` exige `GERENTE`. O fluxo de recuperação por magic link (`reset/request-reset-link` e `reset/magic-link-login`) está bloqueado até ser homologado por uma Change.

## DTOs e recursos

O cliente usa modelos Pydantic em `Projeto_HarleyStore.services.cadastros` para validar os recursos:

- `Cliente` / `ClienteCreate` / `ClienteUpdate`;
- `MotoCliente` / `MotoClienteCreate` / `MotoClienteUpdate`;
- `Produto` / `ProdutoCreate` / `ProdutoUpdate`;
- `Fornecedor` / `FornecedorCreate` / `FornecedorUpdate`;
- `Funcionario` / `FuncionarioCreate` / `FuncionarioUpdate`.

`Produto.codigo` é alfanumérico e único. Os cinco cadastros possuem `ativo`, usado para soft delete. A desativação chama `PATCH` com `ativo = false`; o cliente não deve usar `DELETE` físico para esses recursos.

`Produto.preco_venda` e demais valores financeiros usam validação estrita `> 0` e são serializados como string decimal em JSON. Quantidades de itens usam `> 0` e saldos de estoque usam `>= 0`. Nenhum DTO de escrita envia `id_funcionario`, totais ou datas de autoria.

O `XanoClient` oferece métodos tipados de listagem, criação, atualização e desativação para esses recursos, além da operação HTTP genérica `request(..., base_url=None)`, que permite endereçar outro grupo de APIs.

`ProdutoUpdate` não possui `estoque_qtd`: o saldo é informado somente em `ProdutoCreate` e depois muda apenas por movimentações de estoque.

## Entradas de mercadoria

Os DTOs ficam em `Projeto_HarleyStore.services.entradas`:

- `EntradaMercadoriaCreate` — `id_fornecedor`, `numero_documento` e `itens` (`ItemEntradaCreate`: `id_produto`, `quantidade > 0`, `valor_unitario > 0`); exige ao menos um item e rejeita produto repetido;
- `EntradaMercadoriaResumo` — linha do histórico com `nome_fornecedor`, `nome_funcionario` e `quantidade_itens`;
- `EntradaMercadoriaDetalhe` — resumo com `itens` (`ItemEntrada`, incluindo `codigo`, `nome_produto` e `valor_total_item`).

Métodos:

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `list_entradas()` | `GET entrada_mercadoria` | todos |
| `get_entrada(id)` | `GET entrada_mercadoria/{id}` | todos |
| `registrar_entrada(entrada)` | `POST entrada_mercadoria` | `GERENTE` |

`registrar_entrada` envia somente cabeçalho e itens. `id_funcionario`, `valor_total` e `data_entrada` são definidos pelo Xano, que grava cabeçalho, itens e incremento de estoque na mesma transação. Não existem métodos de edição ou exclusão de entradas: elas são imutáveis.

## Ordens de serviço

Os DTOs ficam em `Projeto_HarleyStore.services.ordens_servico`:

- `OrdemServicoCreate` — `id_moto_cliente`, `id_mecanico` (opcional), `tipo_servico` (`PREVENTIVA` | `CORRETIVA`), `descricao_problema` e `quilometragem` (opcional, `>= 0`);
- `TransicaoStatusOS` — `status_atual` (o status que o usuário está vendo), `status_novo` e `observacao` (obrigatória para `CANCELADA`); valida a tabela `TRANSICOES_OS`, espelho da função Xano `Oficina/validar_transicao_os`;
- `OrdemServicoResumo` — linha da lista com `nome_cliente`, `placa`, `modelo`, `nome_funcionario` (autor) e `nome_mecanico`; os campos da Change 6 são opcionais para OS antigas;
- `OrdemServicoDetalhe` — resumo com `quilometragem`, `motivo_cancelamento`, `historico` (`HistoricoStatusOS`) e `itens` (`ItemOrdemServico`, somente leitura);
- `Mecanico` — `id` e `nome_funcionario`.

Métodos:

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `list_ordens_servico(status=None, id_moto_cliente=None)` | `GET ordens_servico` | todos |
| `get_ordem_servico(id)` | `GET ordens_servico/{id}` | todos |
| `abrir_ordem_servico(ordem)` | `POST ordens_servico` | `GERENTE`, `MECANICO` |
| `transicionar_ordem_servico(id, transicao)` | `POST ordens_servico/{id}/status` | `GERENTE`, `MECANICO` |
| `list_mecanicos()` | `GET oficina/mecanicos` | `GERENTE`, `MECANICO` |

`abrir_ordem_servico` omite campos nulos e nunca envia `status`, `data_abertura`, `id_funcionario` ou `id_cliente`: o Xano define a OS como `ABERTA`, grava o autor a partir do JWT e o cliente a partir da moto. Os filtros de `list_ordens_servico` vão como query string e também servem para o histórico da moto. `PUT`, `PATCH` e `DELETE ordens_servico/{id}` e as mutações de `itens_ordem_servico` respondem `403`.

Uma transição recusada porque a OS mudou (`status_atual` desatualizado) chega como `XanoValidationError`; o Reflex recarrega o detalhe e exibe o status real.

## Erros

| Status HTTP | Exceção | Mensagem da exceção | Mensagem exibida (`feedback.error_feedback`) | Efeito no Reflex |
| --- | --- | --- | --- | --- |
| sem token | `XanoAuthenticationError` | genérica | "Sua sessão expirou. Entre novamente." | limpa a sessão e os estados das páginas; redireciona para `/login` |
| `401` | `XanoAuthenticationError` | genérica | idem | idem |
| `403` | `XanoPermissionError` | genérica | "Seu perfil não possui permissão para esta operação." | preserva a sessão; toast |
| `404` | `XanoNotFoundError` | genérica | "O registro solicitado não foi encontrado." | toast |
| `400` / `422` | `XanoValidationError` | `message` do Xano, se texto com até 200 caracteres; senão genérica | a própria mensagem de negócio | mantém o formulário aberto com a mensagem |
| demais / transporte | `XanoError` | genérica | "Não foi possível comunicar com o Xano. Tente novamente." | toast ou erro da lista |
| `2xx` fora do DTO | `XanoResponseError` | genérica | idem `XanoError` | idem |

Somente o campo `message` de respostas `400`/`422` é propagado; nenhum outro conteúdo do corpo, token ou payload chega às exceções. Os estados Reflex usam `AuthState._xano_error_response` para aplicar a tabela acima de forma uniforme. Quando uma gravação é concluída mas o recarregamento da lista falha, a UI confirma a gravação e mostra o erro apenas na lista.

O cliente não interpreta payloads de domínio. Cada serviço futuro deve definir seus próprios tipos e endpoints sobre esta fronteira.

## Autoria operacional

Endpoints de OS e transações derivam `id_funcionario` do usuário autenticado no Xano: o backend resolve `$auth.id` para `user.id_funcionario` e persiste esse vínculo na criação. `POST`/`PUT` não mapeiam `id_funcionario` do input e os `PATCH` de OS e transações removem a chave (`|unset:"id_funcionario"`) antes de gravar. Um `id_funcionario` enviado pelo frontend nunca é fonte de autoria.

O frontend pode esconder ações incompatíveis com o cargo, mas a autorização final, a autoria e a integridade dos dados permanecem no Xano.

## Matriz de acesso

| Recurso | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Clientes e motos de clientes | escrita | escrita | leitura |
| Produtos e saldo de estoque | escrita (saldo só por movimentação) | leitura | leitura |
| Fornecedores | escrita e leitura | sem acesso | sem acesso |
| Funcionários | escrita e leitura | sem acesso | sem acesso |
| Entradas de mercadoria (histórico e detalhe) | leitura | leitura | leitura |
| Registrar entrada de mercadoria | sim | não | não |
| Criar usuários e enviar email de boas-vindas | sim | não | não |
| Oficina: consultar OS, detalhe e histórico por moto | sim | sim | sim |
| Oficina: abrir OS e transicionar status | sim | não | sim |
| Oficina: listar mecânicos | sim | não | sim |

No Reflex, `ROUTE_ROLES` em `Projeto_HarleyStore/auth.py` espelha essa matriz por rota e alimenta o guard `guarded_page` e os links da sidebar. As rotas protegidas restauram a sessão no `on_load` antes de carregar dados.

## Testes

```bash
python -m unittest discover -s tests
```

- Os testes offline usam `httpx.MockTransport` e contratos estáticos sobre `xano/`; não precisam de rede.
- `tests/test_integration_xano.py` executa chamadas HTTP reais quando `XANO_API_BASE_URL` está configurada (ambiente ou `.env`); caso contrário, é ignorado.
- Credenciais por perfil: `XANO_TEST_GERENTE_EMAIL`/`_PASSWORD`, `XANO_TEST_VENDEDOR_*` e `XANO_TEST_MECANICO_*`. Perfis sem credenciais são ignorados individualmente.
- Os cenários que gravam dados (registro de entrada, documento duplicado, rollback e ciclo completo de OS com as rejeições da máquina de estados) exigem `XANO_TEST_ALLOW_WRITES=true`. Como entradas e OS encerradas são imutáveis, rode-os em um branch ou workspace de testes.
- Os testes de OS exigem a Change 6 publicada; antes do push, os endpoints novos respondem `404`.
