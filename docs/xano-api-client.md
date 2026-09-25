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

### Checklist de deploy da Change 7 (itens de OS e livro de estoque)

1. Publicar com `--sync`: `itens_ordem_servico.id_produto` foi relaxado para anulável (itens do tipo `SERVICO`). Revise antes o `--dry-run`, de preferência num branch.
2. Os demais objetos são aditivos: tabela `movimentacoes_estoque`, campos novos em `itens_ordem_servico`, `ordens_servico` e `produtos`, funções `Estoque/movimentar_estoque` e `Oficina/totais_os`, rotas `POST`/`DELETE ordens_servico/{id}/itens`.
3. Rodar a suíte de integração com `XANO_TEST_ALLOW_WRITES=true` e, para validar as travas de concorrência, `XANO_TEST_CONCURRENCY=true`.

## Autenticação

A instância autenticada recebe o JWT através do argumento `token`. O cliente envia o cabeçalho:

```text
Authorization: Bearer <JWT>
```

O cliente não persiste tokens, não os registra em logs e não os envia em query strings. O Reflex guarda o JWT no cookie `harley_auth_token` e restaura a sessão com `auth/me` no `on_load` de cada rota protegida.

`auth/me` devolve `{user, funcionario}`. `XanoEmployee.ativo` indica se o funcionário vinculado está ativo; o Reflex recusa a sessão de funcionário inativo, e o Xano (`enforce_role`) nega qualquer operação de negócio a ele.

Somente `auth/login` é público. `auth/signup` exige `GERENTE`, cria o usuário vinculado a um funcionário ativo e ainda sem usuário, e **não** devolve token do novo usuário. `message/send_welcome_email` exige `GERENTE`. O fluxo de recuperação por magic link (`reset/request-reset-link` e `reset/magic-link-login`) está bloqueado até ser homologado por uma Change.

`reset/update_password` troca a senha do próprio usuário autenticado e exige `current_password`, `password` (mínimo de 8 caracteres) e `confirm_password`. O Xano valida o funcionário vinculado ativo (`enforce_role`), confere a senha atual com `security.check_password` e rejeita a nova senha igual à atual, com `400` e mensagem legível. As senhas não passam por `trim`, como em `auth/login` e `auth/signup`, e o log registra apenas o id do usuário. Ainda não há tela nem método no `XanoClient` para essa troca.

## DTOs e recursos

O cliente usa modelos Pydantic em `Projeto_HarleyStore.services.cadastros` para validar os recursos:

- `Cliente` / `ClienteCreate` / `ClienteUpdate`;
- `MotoCliente` / `MotoClienteCreate` / `MotoClienteUpdate`;
- `Produto` / `ProdutoCreate` / `ProdutoUpdate`;
- `Fornecedor` / `FornecedorCreate` / `FornecedorUpdate`;
- `Funcionario` / `FuncionarioCreate` / `FuncionarioUpdate`.

`Produto.codigo` é alfanumérico e único. Os cinco cadastros possuem `ativo`, usado para soft delete. A desativação chama `PATCH` com `ativo = false`. Desde o saneamento pós-Change 7, o `DELETE` físico de clientes, motos de clientes, produtos, fornecedores, funcionários, motos da loja e transações responde `403`; a única exclusão física do sistema é a remoção de item de OS aberta.

`Produto` (modelo de leitura) trata `estoque_qtd` nulo, possível em registros legados do Xano, como `0`, a mesma leitura de `Estoque/movimentar_estoque`. `ProdutoCreate` continua exigindo um saldo inicial válido.

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

`registrar_entrada` envia somente cabeçalho e itens. `id_funcionario`, `valor_total` e `data_entrada` são definidos pelo Xano, que grava cabeçalho, itens e incremento de estoque na mesma transação. O incremento passa por `Estoque/movimentar_estoque` e gera uma linha `ENTRADA` no livro de movimentações. Não existem métodos de edição ou exclusão de entradas: elas são imutáveis.

## Livro de movimentações de estoque

Toda alteração de `produtos.estoque_qtd` depois da criação do produto passa pela função Xano `Estoque/movimentar_estoque`, sempre dentro da transação de quem a chama:

| Tipo | Origem | Efeito |
| --- | --- | --- |
| `ENTRADA` | `POST entrada_mercadoria` | soma a quantidade |
| `SAIDA_OS` | inclusão de peça na OS | subtrai; rejeita saldo insuficiente e produto inativo |
| `ESTORNO_OS` | remoção de peça ou cancelamento da OS | soma a quantidade baixada |

Cada movimentação grava em `movimentacoes_estoque` o saldo anterior e posterior, o funcionário autenticado e a origem. O índice único `(id_produto, versao_anterior)`, somado a `produtos.versao_estoque`, faz a segunda movimentação concorrente do mesmo produto falhar e desfazer a transação inteira. O livro não tem endpoints nem métodos no cliente nesta etapa.

## Ordens de serviço

Os DTOs ficam em `Projeto_HarleyStore.services.ordens_servico`:

- `OrdemServicoCreate` — `id_moto_cliente`, `id_mecanico` (opcional), `tipo_servico` (`PREVENTIVA` | `CORRETIVA`), `descricao_problema` e `quilometragem` (opcional, `>= 0`);
- `TransicaoStatusOS` — `status_atual` (o status que o usuário está vendo), `status_novo` e `observacao` (obrigatória para `CANCELADA`); valida a tabela `TRANSICOES_OS`, espelho da função Xano `Oficina/validar_transicao_os`;
- `OrdemServicoResumo` — linha da lista com `nome_cliente`, `placa`, `modelo`, `nome_funcionario` (autor), `nome_mecanico` e `valor_total`; os campos das Changes 6 e 7 são opcionais para OS antigas;
- `OrdemServicoDetalhe` — resumo com `quilometragem`, `motivo_cancelamento`, `valor_pecas`, `valor_servicos`, `historico` (`HistoricoStatusOS`) e `itens` (`ItemOrdemServico`);
- `ItemOSCreate` — `tipo_item` (`PECA` | `SERVICO`), `id_produto` (peça), `descricao` e `valor_unitario` (serviço, `> 0`, duas casas) e `quantidade > 0`; a peça descarta descrição e valor, porque o preço vem do produto, e o serviço descarta o produto;
- `ItemOrdemServico` — item lido, com `tipo_item` (nulo em itens legados, lido como `PECA`), `valor_unitario`, `valor_total_item` e `estoque_baixado`;
- `Mecanico` — `id` e `nome_funcionario`.

Métodos:

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `list_ordens_servico(status=None, id_moto_cliente=None)` | `GET ordens_servico` | todos |
| `get_ordem_servico(id)` | `GET ordens_servico/{id}` | todos |
| `abrir_ordem_servico(ordem)` | `POST ordens_servico` | `GERENTE`, `MECANICO` |
| `transicionar_ordem_servico(id, transicao)` | `POST ordens_servico/{id}/status` | `GERENTE`, `MECANICO` |
| `list_mecanicos()` | `GET oficina/mecanicos` | `GERENTE`, `MECANICO` |
| `adicionar_item_ordem_servico(id, item)` | `POST ordens_servico/{id}/itens` | `GERENTE`, `MECANICO` |
| `remover_item_ordem_servico(id, item_id)` | `DELETE ordens_servico/{id}/itens/{item_id}` | `GERENTE`, `MECANICO` |

`abrir_ordem_servico` omite campos nulos e nunca envia `status`, `data_abertura`, `id_funcionario` ou `id_cliente`: o Xano define a OS como `ABERTA`, grava o autor a partir do JWT e o cliente a partir da moto. Os filtros de `list_ordens_servico` vão como query string e também servem para o histórico da moto. `PUT`, `PATCH` e `DELETE ordens_servico/{id}` e as rotas legadas de mutação de `itens_ordem_servico` respondem `403`.

Uma transição recusada porque a OS mudou (`status_atual` desatualizado) chega como `XanoValidationError`; o Reflex recarrega o detalhe e exibe o status real.

### Itens da OS

As duas rotas de itens devolvem o `OrdemServicoDetalhe` atualizado e só aceitam OS `ABERTA` ou `EM_ANDAMENTO`:

- **Peça:** o Xano grava `valor_unitario = produtos.preco_venda` (fotografia), `valor_total_item = quantidade × valor_unitario` e baixa o estoque na mesma transação (`SAIDA_OS`). Produto inativo, produto já presente na OS e quantidade acima do saldo são rejeitados com `400` ("Saldo insuficiente para <código>: disponível X, solicitado Y.").
- **Serviço:** descrição e valor informados, sem movimentação de estoque.
- **Remoção:** a peça baixada volta ao estoque (`ESTORNO_OS`); serviços e itens legados (`estoque_baixado` diferente de `true`) não movimentam estoque.
- **Cancelamento da OS:** devolve todas as peças baixadas na mesma transação da transição; concluir não movimenta estoque. Os itens e totais da OS cancelada ficam como registro.
- **Totais:** a cada mutação o Xano grava `valor_pecas`, `valor_servicos` e `valor_total` na OS (usados pela lista); o detalhe sempre os recalcula a partir dos itens (`Oficina/totais_os`).
- **Concorrência:** toda mutação da OS começa atualizando `ordens_servico.atualizado_em`, o que trava a linha e serializa inclusões, remoções e transições da mesma OS. Uma falha dentro da transação (corrida) responde `400` "O estoque ou a OS foram alterados por outra operação. Atualize e tente novamente."; o Reflex recarrega detalhe, itens e saldos.

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
| Oficina: incluir e remover peças e serviços em OS aberta ou em andamento | sim | não | sim |
| Oficina: listar mecânicos | sim | não | sim |

No Reflex, `ROUTE_ROLES` em `Projeto_HarleyStore/auth.py` espelha essa matriz por rota e alimenta o guard `guarded_page` e os links da sidebar. As rotas protegidas restauram a sessão no `on_load` antes de carregar dados.

## Testes

```bash
python -m unittest discover -s tests
```

- Os testes offline usam `httpx.MockTransport` e contratos estáticos sobre `xano/`; não precisam de rede.
- `tests/test_integration_xano.py` executa chamadas HTTP reais quando `XANO_API_BASE_URL` está configurada (ambiente ou `.env`); caso contrário, é ignorado.
- Credenciais por perfil: `XANO_TEST_GERENTE_EMAIL`/`_PASSWORD`, `XANO_TEST_VENDEDOR_*` e `XANO_TEST_MECANICO_*`. Perfis sem credenciais são ignorados individualmente.
- Os cenários que gravam dados (registro de entrada, documento duplicado, rollback, ciclo completo de OS com as rejeições da máquina de estados, e ciclo de itens com baixa, devolução, totais e cancelamento) exigem `XANO_TEST_ALLOW_WRITES=true`. Como entradas, OS encerradas e movimentações de estoque são imutáveis, rode-os em um branch ou workspace de testes. As OS abertas pelos testes são canceladas ao final, devolvendo as peças.
- `XANO_TEST_CONCURRENCY=true` (junto com as escritas) roda as corridas: duas OS disputando todo o saldo de um produto e uma inclusão simultânea ao cancelamento. Exige duas motos de cliente sem OS em aberto.
- Os testes de cada Change exigem o respectivo push; antes dele, os endpoints novos respondem `404`.
