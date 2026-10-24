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
- Desde 2026-10-15, o token do Swagger em `xano/api/harley/harley.xs` é o placeholder `YOUR_XANO_SWAGGER_TOKEN`; o valor real continua no histórico do Git. Antes de qualquer push, desligue o Swagger público (`xano workspace edit --no-swagger`) ou gere um token novo, e confira se o `--dry-run` lista o grupo `HARLEY`: publicar o placeholder pode trocar o token do Swagger por um valor conhecido. Um `xano workspace pull` traz o token real de volta ao arquivo.
- Não rode `xano workspace pull` dentro de `xano/`. Além de trazer o token, a CLI 1.3.x grava 6 endpoints em pastas aninhadas (por exemplo, `motos/motos_id/reserva_POST.xs` no lugar de `motos/motos_id_reserva_POST.xs`) e não apaga os arquivos que já existem (conferido em 2026-10-22): esses endpoints ficariam em dobro no próximo push. Para conferir mudanças feitas no painel, puxe numa pasta temporária fora do projeto, compare com `xano/` e apague a pasta, porque ela contém o token.

### Checklist pós-deploy da Change 5 e do saneamento

1. Publicar com `--sync` (o schema de `entrada_mercadoria` relaxou `numero_documento` e `id_funcionario` para anuláveis).
2. Executar uma vez a função `Estoque/normalizar_entradas_legadas`: entradas antigas sem documento passam a `LEGADO-<id>`.
3. Conferir que não há produtos antigos com `codigo` vazio repetido; o índice único de `produtos.codigo` falharia na criação.
4. Rodar a suíte de integração (seção "Testes de integração").

### Checklist de deploy da Change 11 (venda de balcão)

1. Revisar o `--dry-run`. Esperado, sem exclusões e sem `--sync`:
   - `itens_transacao` criada;
   - `movimentacoes_estoque` com `ADD_FIELD` (`id_transacao`) e `UPDATE_FIELD` (enum `tipo` com `SAIDA_VENDA`);
   - `Balcao/detalhe_venda` criada; `Estoque/movimentar_estoque` atualizada;
   - `balcao/vendas POST` criado.
2. Publicar com `xano workspace push -d ./xano` (publicado em 2026-10-11).
3. Conferir com um `pull` que o enum do livro tem `SAIDA_VENDA` (confirmado em 2026-10-11).
4. Rodar a integração: `XANO_TEST_LIVE=true` (mecânico barrado e carrinhos inválidos), `XANO_TEST_ALLOW_WRITES=true` (consumidor final, cliente com repetição da chave, saldo insuficiente e preço alterado) e `XANO_TEST_CONCURRENCY=true` (duas vendas pelo saldo inteiro).

O `--dry-run` sempre lista `UPDATE table modelos_moto`: o remoto tem o padrão `false` em `destaque`, mas o texto que ele guarda não o traz. Nenhum push parcial alinha isso, e a diferença é só cosmética.

### Checklist de deploy da Change 10 (fechamento financeiro)

1. Revisar `xano workspace push -d ./xano --dry-run`. Esperado, sem exclusões e sem `--sync`:
   - `transacoes`: `ADD_FIELD` (`id_os`, anulável) e índice simples;
   - funções criadas: `Financeiro/resumo_operacoes` e `Financeiro/lancar_os_concluidas_legadas`; `Oficina/detalhe_os` atualizada;
   - `financeiro/resumo GET` criado; `ordens_servico/{id}/status POST`, `transacoes POST` e `transacoes/{id} PUT/PATCH` atualizados;
   - a diferença anterior em `modelos_moto` (padrão de `destaque`) não faz parte da Change 10.
2. Publicar com `xano workspace push -d ./xano`.
3. Executar uma vez `Financeiro/lancar_os_concluidas_legadas` (Run & Debug) com o id de um `GERENTE` ativo: lança a receita das OS concluídas antes do push. Pode ser repetida sem duplicar.
4. Conferir em `/financeiro` as transações antigas criadas pelo CRUD genérico, que entram no resumo como estão.
5. Rodar a integração: `XANO_TEST_LIVE=true` (acesso, imutabilidade, período) e `XANO_TEST_ALLOW_WRITES=true` (conclusão de OS gera um único lançamento visível no resumo; OS vazia e cancelada não geram); `XANO_TEST_CONCURRENCY=true` para duas conclusões simultâneas.

### Checklist de deploy do saneamento pós-Change 9

1. Revisar `xano workspace push -d ./xano --dry-run`: só atualizações de 8 endpoints (`transacoes` GET/POST, `transacoes/{id}` GET/PUT/PATCH/DELETE, `entrada_mercadoria` POST e `logs/user/my_events` GET), sem `--sync`. A diferença em `modelos_moto` (padrão de `destaque`) é anterior e não faz parte deste saneamento.
2. Publicar com `xano workspace push -d ./xano`.
3. Desligar o Swagger público do workspace ou exigir token (`xano workspace edit --no-swagger`, ou pelo painel): o token do grupo `HARLEY` fica em texto puro no export versionado (`xano/api/harley/harley.xs`) e não protege nada num repositório público.
4. Rodar a integração (`XANO_TEST_LIVE=true` para os 403 de RBAC sem gravar dados; `XANO_TEST_ALLOW_WRITES=true` para a suíte completa).

### Checklist de deploy da Change 9 (fechamento de vendas de motos)

1. Revisar `xano workspace push -d ./xano --dry-run`: `motos_clientes.placa` passa a anulável (relaxamento; o índice único continua), e `Vendas/vender_moto` e `POST vender_moto` aceitam placa opcional. Se o push não aplicar a mudança do campo, publicar com `--sync`, de preferência num branch.
2. Publicar com `xano workspace push -d ./xano`.
3. Rodar a integração com `XANO_TEST_ALLOW_WRITES=true` (venda sem placa, venda repetida, reserva de outro cliente) e `XANO_TEST_CONCURRENCY=true` (duas vendas simultâneas). As vendas de teste ficam no banco.

### Checklist de deploy da Change 8 (catálogo e reservas de motos)

1. Publicar com `xano workspace push -d ./xano` (aditivo: tabelas `modelos_moto` e `historico_status_moto`, campos anuláveis em `motos`, funções `Catalogo/*` e `Vendas/*`, endpoints de catálogo, unidades e reservas).
2. Executar uma vez a função `Catalogo/seed_exemplo` (Run & Debug), informando o id de um funcionário `GERENTE`, para ter um modelo por família com cores e unidades. As imagens são placeholders neutros (`placehold.co`): troque-as por fotos próprias ou licenciadas antes de divulgar `/catalogo`.
3. Rodar a integração (seção "Testes").

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

Além de `auth/login`, somente a vitrine é pública: `GET catalogo` e `GET catalogo/{id}` (Change 8), de leitura e com projeção fechada. `auth/signup` exige `GERENTE`, cria o usuário vinculado a um funcionário ativo e ainda sem usuário, e **não** devolve token do novo usuário. `message/send_welcome_email` exige `GERENTE`. O fluxo de recuperação por magic link (`reset/request-reset-link` e `reset/magic-link-login`) está bloqueado até ser homologado por uma Change.

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

As validações (fornecedor e produtos ativos, documento ainda não registrado) rodam antes da transação e devolvem `400` com mensagem própria. Dentro da transação ficam só as gravações, protegidas por `try_catch`: uma corrida (mesmo documento ou mesmo produto ao mesmo tempo) viola um índice único, desfaz tudo e responde `400` "A entrada não foi registrada: o documento ou o estoque foram alterados por outra operação. Atualize e tente novamente." em vez de um `500`.

## Livro de movimentações de estoque

Toda alteração de `produtos.estoque_qtd` depois da criação do produto passa pela função Xano `Estoque/movimentar_estoque`, sempre dentro da transação de quem a chama:

| Tipo | Origem | Efeito |
| --- | --- | --- |
| `ENTRADA` | `POST entrada_mercadoria` | soma a quantidade |
| `SAIDA_OS` | inclusão de peça na OS | subtrai; rejeita saldo insuficiente e produto inativo |
| `ESTORNO_OS` | remoção de peça ou cancelamento da OS | soma a quantidade baixada |

Cada movimentação grava em `movimentacoes_estoque` o saldo anterior e posterior, o funcionário autenticado e a origem. O índice único `(id_produto, versao_anterior)`, somado a `produtos.versao_estoque`, faz a segunda movimentação concorrente do mesmo produto falhar e desfazer a transação inteira. O livro não tem endpoints nem métodos no cliente nesta etapa.

## Catálogo de motos (vitrine)

Os DTOs ficam em `Projeto_HarleyStore.services.catalogo`:

- `VariacaoCor` — `nome`, `hex` (`#RRGGBB`) e `imagem_url` (`https://`);
- `ModeloMotoCreate` / `ModeloMotoUpdate` — nome, `familia` (`TOURING` | `CRUISER` | `ADVENTURE` | `SPORT`), descrição, `preco_base > 0`, `imagem_principal` (`https://`), até 12 `variacoes_cor`, `destaque` e, no update, `ativo`;
- `ModeloMoto` — modelo gerido pelo gerente, inclusive inativo;
- `ModeloCatalogo` — projeção de vitrine: dados públicos do modelo, `preco_a_partir` e `disponiveis`.

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `list_catalogo(familia=None, busca=None)` | `GET catalogo` | público (sem token) |
| `get_modelo_catalogo(id)` | `GET catalogo/{id}` | público (sem token) |
| `list_modelos_moto()` | `GET modelos_moto` | `GERENTE` |
| `criar_modelo_moto(modelo)` | `POST modelos_moto` | `GERENTE` |
| `atualizar_modelo_moto(id, modelo)` | `PATCH modelos_moto/{id}` | `GERENTE` |

- **Projeção pública:** a função `Catalogo/vitrine` devolve só modelos ativos e só os campos `id`, `nome_modelo`, `familia`, `descricao`, `imagem_principal`, `variacoes_cor`, `destaque`, `preco_a_partir` e `disponiveis`. Nunca expõe unidades, chassi, cliente, vendedor ou histórico. As unidades são lidas numa única consulta (sem N+1).
- **"A partir de":** menor `preco_venda` entre as unidades `DISPONIVEL` do modelo; sem unidades, vale o `preco_base` ("Sob consulta" na vitrine).
- **Cache e `429`:** a vitrine passa pelo mesmo backend Reflex para todos os visitantes. `catalogo_cache` (TTL de 60 s, por processo) guarda a lista completa; a tela filtra família e busca localmente e só a recarrega depois do TTL ou de uma escrita do gerente (`invalidate`). Uma resposta `429` vira `XanoRateLimitError`, com a mensagem "Muitas requisições ao Xano. Aguarde alguns segundos e tente novamente.".

## Estoque e reservas de motos

Os DTOs ficam em `Projeto_HarleyStore.services.motos`:

- `MotoEstoqueCreate` — `id_modelo`, `chassi` (VIN de 17 caracteres, normalizado em caixa alta), `cor`, `ano_modelo` (de 1990 ao ano seguinte) e `preco_venda > 0`; nunca carrega status, cliente ou vendedor;
- `MotoEstoqueUpdate` — `chassi`, `cor`, `ano_modelo` e `preco_venda`, opcionais;
- `MotoEstoque` / `MotoEstoqueDetalhe` — unidade enriquecida (modelo, família, cores, cliente, vendedor, validade) e, no detalhe, `historico` (`HistoricoStatusMoto`); `status` nulo de unidades legadas é lido como `DISPONIVEL`;
- `ReservaMotoCreate` — `id_cliente`, `dias_validade` (1 a 30, padrão 7) e `observacao`;
- `CancelamentoReservaMoto` — `motivo` obrigatório;
- `VendaMotoCreate` — `id_moto`, `id_cliente`, `valor_venda > 0` (duas casas), `placa` opcional (normalizada para caixa alta sem hífen ou espaços, padrão `ABC1234` ou `ABC1D23`; em branco vira ausente) e `observacao` (até 500); nunca carrega `id_funcionario`;
- `VendaMotoResultado` — `id_transacao`, `id_moto_cliente` e `status` (`SUCESSO`).

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `list_motos_estoque(status=None, id_modelo=None)` | `GET motos` | `GERENTE`, `VENDEDOR` |
| `get_moto_estoque(id)` | `GET motos/{id}` | `GERENTE`, `VENDEDOR` |
| `cadastrar_moto_estoque(moto)` | `POST motos` | `GERENTE` |
| `atualizar_moto_estoque(id, moto)` | `PATCH motos/{id}` | `GERENTE` |
| `reservar_moto(id, reserva)` | `POST motos/{id}/reserva` | `GERENTE`, `VENDEDOR` |
| `cancelar_reserva_moto(id, cancelamento)` | `POST motos/{id}/reserva/cancelar` | `GERENTE`, `VENDEDOR` (regra abaixo) |
| `vender_moto(venda)` | `POST vender_moto` | `GERENTE`, `VENDEDOR` |

- **Status:** muda somente por `Vendas/transicionar_moto`, chamada dentro da transação da reserva, do cancelamento e da venda; `PUT` e `DELETE motos/{id}` respondem `403`.
- **Reserva:** unidade `DISPONIVEL` com modelo, cliente ativo; vendedor (do JWT) e validade (`now + dias`) definidos pelo servidor.
- **Cancelamento:** quem reservou, um `GERENTE` ou, depois do vencimento, qualquer vendedor; outros recebem `403`.
- **Concorrência:** cada transição grava `historico_status_moto` com `versao_anterior` antes da unidade; o índice único `(id_moto, versao_anterior)` faz a segunda reserva simultânea falhar (`400`).
- **Cadastro:** chassi único em `motos` e em `motos_clientes`; cor dentro das variações do modelo; a unidade nasce `DISPONIVEL` com histórico.
- **Legado:** `list_motos`, `create_moto`, `update_moto` e os DTOs `Moto`/`MotoCreate`/`MotoUpdate` foram removidos.

### Venda (`POST vender_moto`, Change 9)

`vender_moto` envia o corpo com `exclude_none`: placa e observação ausentes não vão no JSON. O funcionário vem do JWT. O contrato completo está em `openspec/changes/fechamento-venda-motos/design.md`.

- **Efeito:** numa única `db.transaction`, cria a moto do cliente (`motos_clientes`, com o nome do modelo comercial, o chassi da unidade e a placa ou nulo), registra a transação `MOTO` (`valor_total = valor_venda`) e passa a unidade a `VENDIDA` com o comprador.
- **Regras:** unidade `DISPONIVEL` para qualquer cliente ativo ou `RESERVADA` somente para o cliente da reserva; a unidade precisa de chassi; chassi e placa informada não podem existir em `motos_clientes`.
- **Recusas (`400`, mensagem do Xano):** "Esta moto já foi vendida.", "Esta moto está reservada para outro cliente.", "Cadastre o chassi desta moto antes de vendê-la.", "Cliente inativo ou inexistente.", "Chassi já cadastrado em uma moto de cliente.", "Placa já cadastrada em uma moto de cliente." e, numa corrida, "A moto foi alterada por outro usuário. Atualize e tente novamente.". Unidade inexistente: `404`.
- **Reflex:** uma recusa `400`/`404` recarrega a lista de `/vendas`; se a unidade não está mais vendável para o cliente escolhido, o modal fecha e a notificação mostra a mensagem; senão, o modal continua com o erro. Uma venda aceita invalida o `catalogo_cache` e recarrega a lista.

## Ordens de serviço

Os DTOs ficam em `Projeto_HarleyStore.services.ordens_servico`:

- `OrdemServicoCreate` — `id_moto_cliente`, `id_mecanico` (opcional), `tipo_servico` (`PREVENTIVA` | `CORRETIVA`), `descricao_problema` e `quilometragem` (opcional, `>= 0`);
- `TransicaoStatusOS` — `status_atual` (o status que o usuário está vendo), `status_novo` e `observacao` (obrigatória para `CANCELADA`); valida a tabela `TRANSICOES_OS`, espelho da função Xano `Oficina/validar_transicao_os`;
- `OrdemServicoResumo` — linha da lista com `nome_cliente`, `placa`, `modelo`, `nome_funcionario` (autor), `nome_mecanico` e `valor_total`; os campos das Changes 6 e 7 são opcionais para OS antigas;
- `OrdemServicoDetalhe` — resumo com `quilometragem`, `motivo_cancelamento`, `valor_pecas`, `valor_servicos`, `historico` (`HistoricoStatusOS`), `itens` (`ItemOrdemServico`) e, desde a Change 10, `id_transacao` e `data_lancamento` (receita lançada na conclusão; nulos sem lançamento);
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

**Faturamento (Change 10):** a transição para `CONCLUIDA` grava, na mesma transação, a receita `ORDEM_SERVICO` com o total recalculado dos itens, o `id_os`, o cliente e a moto da OS e o funcionário do JWT. OS com total zero conclui sem lançamento; se o lançamento falhar, nada é gravado e a resposta é o `400` de conflito. O detalhe mostra "Faturada · transação #N", e o painel de conclusão avisa o valor que será lançado.

### Itens da OS

As duas rotas de itens devolvem o `OrdemServicoDetalhe` atualizado e só aceitam OS `ABERTA` ou `EM_ANDAMENTO`:

- **Peça:** o Xano grava `valor_unitario = produtos.preco_venda` (fotografia), `valor_total_item = quantidade × valor_unitario` e baixa o estoque na mesma transação (`SAIDA_OS`). Produto inativo, produto já presente na OS e quantidade acima do saldo são rejeitados com `400` ("Saldo insuficiente para <código>: disponível X, solicitado Y.").
- **Serviço:** descrição e valor informados, sem movimentação de estoque.
- **Remoção:** a peça baixada volta ao estoque (`ESTORNO_OS`); serviços e itens legados (`estoque_baixado` diferente de `true`) não movimentam estoque.
- **Cancelamento da OS:** devolve todas as peças baixadas na mesma transação da transição; concluir não movimenta estoque. Os itens e totais da OS cancelada ficam como registro.
- **Totais:** a cada mutação o Xano grava `valor_pecas`, `valor_servicos` e `valor_total` na OS (usados pela lista); o detalhe sempre os recalcula a partir dos itens (`Oficina/totais_os`).
- **Concorrência:** toda mutação da OS começa atualizando `ordens_servico.atualizado_em`, o que trava a linha e serializa inclusões, remoções e transições da mesma OS. Uma falha dentro da transação (corrida) responde `400` "O estoque ou a OS foram alterados por outra operação. Atualize e tente novamente."; o Reflex recarrega detalhe, itens e saldos.

## Financeiro (Change 10)

Os DTOs ficam em `Projeto_HarleyStore.services.financeiro`:

- `PeriodoFinanceiro` — `inicio` e `fim` (datas, inclusivas, de 1 a 366 dias); `params()` gera os limites do dia em UTC−3 fixo (`FUSO_LOJA`), em milissegundos (00:00:00.000 e 23:59:59.999);
- `ResumoFinanceiro` — `receitas`, `despesas`, `saldo`, `por_tipo` (`TotalPorTipo`), `operacoes` (`OperacaoFinanceira`), `total_operacoes` e `truncado`;
- `OperacaoFinanceira` — `origem` (`TRANSACAO` | `ENTRADA`), `tipo`, `natureza` (`RECEITA` | `DESPESA`), `data`, `valor`, `contraparte` (cliente ou fornecedor), `funcionario` e as referências (`id_os`, `id_moto_cliente`, `modelo`, `placa`, `id_entrada`, `numero_documento`).

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `resumo_financeiro(periodo)` | `GET financeiro/resumo?inicio=&fim=` | `GERENTE` |

- **Resumo:** une as transações do período (receitas; `COMPRA` antigas como despesa) e as entradas de mercadoria (despesas). Os totais cobrem o período inteiro; a lista traz as 500 operações mais recentes. Período invertido ou maior que 366 dias responde `400`.
- **Imutabilidade:** não há método de escrita de transações. `POST transacoes` e `PUT`/`PATCH`/`DELETE transacoes/{id}` respondem `403` para qualquer perfil; `GET transacoes[/{id}]` é só do `GERENTE`.
- **Retroativo:** a função `Financeiro/lancar_os_concluidas_legadas` (Run & Debug, nunca chamada por endpoint) lança as OS concluídas antes da Change 10.
- **Tela `/financeiro`:** período com atalhos, cartões de receitas, despesas e saldo, totais por tipo e lista de operações com filtro por tipo e busca locais (sem nova chamada ao Xano).

## Venda no balcão (Change 11)

Os DTOs ficam em `Projeto_HarleyStore.services.balcao`:

- `VendaBalcaoCreate` — `chave_venda` (UUID do carrinho), `id_cliente` opcional, `total_esperado` (2 casas) e de 1 a 30 `itens` (`ItemVendaBalcaoCreate`: `id_produto` sem repetição e `quantidade`). Preço, total por item e vendedor nunca vão no payload;
- `VendaBalcaoDetalhe` — recibo: `id_transacao`, `data_transacao`, `valor_total`, cliente e vendedor (com nomes) e `itens` (`ItemVendaBalcao`, com código, nome e preço fotografado).

| Método | Endpoint | Perfil |
| --- | --- | --- |
| `vender_balcao(venda)` | `POST balcao/vendas` | `GERENTE`, `VENDEDOR` |

- **Atomicidade:** transação `BALCAO`, itens em `itens_transacao` e uma saída `SAIDA_VENDA` por item, numa única `db.transaction`, em ordem crescente de produto.
- **Validações (`400`, sem gravar):** carrinho vazio ou com mais de 30 itens, produto repetido ou inativo, cliente inativo, saldo insuficiente e total diferente do recalculado ("Os preços mudaram…"). Uma corrida dentro da transação responde a mensagem de conflito.
- **Idempotência:** a mesma `chave_venda` devolve a venda já registrada. O Reflex mantém a chave nas novas tentativas (timeout, resposta perdida) e só a renova após uma venda concluída ou ao limpar o carrinho.
- **Tela `/balcao`:** filtro por categoria e busca local, carrinho, cliente opcional ("Consumidor final"), confirmação com o botão travado durante o envio e recibo.

## Erros

| Status HTTP | Exceção | Mensagem da exceção | Mensagem exibida (`feedback.error_feedback`) | Efeito no Reflex |
| --- | --- | --- | --- | --- |
| sem token | `XanoAuthenticationError` | genérica | "Sua sessão expirou. Entre novamente." | limpa a sessão e os estados das páginas; redireciona para `/login` |
| `401` | `XanoAuthenticationError` | genérica | idem | idem |
| `403` | `XanoPermissionError` | genérica | "Seu perfil não possui permissão para esta operação." | preserva a sessão; toast |
| `404` | `XanoNotFoundError` | genérica | "O registro solicitado não foi encontrado." | toast |
| `429` | `XanoRateLimitError` | genérica | "Muitas requisições ao Xano. Aguarde alguns segundos e tente novamente." | toast ou erro da lista; a vitrine usa cache de 60 s |
| `400` / `422` | `XanoValidationError` | `message` do Xano, se texto com até 200 caracteres; senão genérica | a própria mensagem de negócio | mantém o formulário aberto com a mensagem |
| transporte (timeout, conexão) | `XanoConnectionError` | genérica | "Sem conexão com o Xano. Verifique a internet e tente novamente." | toast ou erro da lista; log `WARNING` |
| `5xx` | `XanoError` | genérica | "O Xano teve um erro interno. O problema foi registrado; tente novamente em instantes." | toast ou erro da lista; log `ERROR` |
| demais | `XanoError` | genérica | "Não foi possível comunicar com o Xano. Tente novamente." | toast ou erro da lista |
| `2xx` fora do DTO | `XanoResponseError` | genérica | "O Xano enviou dados fora do formato esperado. O problema foi registrado; avise o responsável pelo sistema." | toast ou erro da lista; log `WARNING` |

**Leitura tolerante (Change 15).** As listas (`XanoClient._list`) são validadas registro a registro.

- Um registro fora do contrato de leitura é descartado e gera um log `WARNING` com endpoint, índice, `id` e os campos e tipos do erro, nunca os valores.
- Uma resposta que não é lista, ou sem nenhum registro válido, continua sendo `XanoResponseError`.
- Os DTOs de leitura são separados dos de escrita. Campos de exibição (textos, imagens, cores, preço de vitrine) aceitam nulo e formatos fora do padrão com valor padrão; uma `imagem_url` que não seja `http(s)` ou caminho local vira vazio.
- Identidade, vínculo e regras de negócio continuam estritos: ids, chaves, enums, saldo ≥ 0 e preço de peça > 0.
- Os logs saem pelo logger `Projeto_HarleyStore.services.xano_client` na saída do backend do Reflex.

Somente o campo `message` de respostas `400`/`422` é propagado; nenhum outro conteúdo do corpo, token ou payload chega às exceções. Os estados Reflex usam `AuthState._xano_error_response` para aplicar a tabela acima de forma uniforme. Quando uma gravação é concluída mas o recarregamento da lista falha, a UI confirma a gravação e mostra o erro apenas na lista.

O cliente não interpreta payloads de domínio. Cada serviço futuro deve definir seus próprios tipos e endpoints sobre esta fronteira.

## Autoria operacional

Endpoints de OS e transações derivam `id_funcionario` do usuário autenticado no Xano: o backend resolve `$auth.id` para `user.id_funcionario` e persiste esse vínculo na criação. `POST` não mapeia `id_funcionario` do input e o `PATCH` de OS (bloqueado) nunca grava a chave. Transações não têm escrita manual desde a Change 10: nascem da venda e da conclusão de OS, sempre com o funcionário do JWT. Um `id_funcionario` enviado pelo frontend nunca é fonte de autoria.

Todo endpoint com `auth = "user"` chama `Quick Start/enforce_role` (funcionário vinculado, existente, ativo e com o papel mínimo); a exceção é `auth/me`, que devolve só a identidade de quem chama. Um teste de contrato (`test_every_authenticated_endpoint_enforces_an_employee_role`) impede regressões.

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
| Catálogo de motos (vitrine `/catalogo`) | sim | sim | sim (também visitantes sem login) |
| Estoque de motos, reservas e histórico (`/vendas`) | sim | sim | não |
| Reservar unidade disponível | sim | sim | não |
| Cancelar reserva | qualquer | própria ou vencida | não |
| Vender unidade (disponível, ou reservada ao cliente da reserva) | sim | sim | não |
| Criar e editar modelos e unidades | sim | não | não |
| Consultar transações (`GET transacoes[/{id}]`) | sim | não | não |
| Lançar, corrigir ou excluir transação manualmente (`POST`/`PUT`/`PATCH`/`DELETE transacoes`) | não | não | não |
| Visão consolidada (`/financeiro`, `GET financeiro/resumo`) | sim | não | não |
| Concluir OS (gera a receita `ORDEM_SERVICO`) | sim | não | sim |
| Vender no balcão (`/balcao`, `POST balcao/vendas`; gera a receita `BALCAO`) | sim | sim | não |

No Reflex, `ROUTE_ROLES` em `Projeto_HarleyStore/auth.py` espelha essa matriz por rota e alimenta o guard `guarded_page` e os links da sidebar. As rotas protegidas restauram a sessão no `on_load` antes de carregar dados.

## Testes

```bash
pip install -r requirements-dev.txt     # pytest
python -m pytest                        # suíte completa; a integração real fica ignorada
python -m pytest -m "not integration"   # somente offline
XANO_TEST_LIVE=true python -m pytest -m integration          # integração só de leitura
XANO_TEST_ALLOW_WRITES=true python -m pytest -m integration  # integração completa
```

- O pytest é o executor (`pytest.ini`: `testpaths`, `-ra` para listar o motivo de cada teste ignorado e marcadores estritos). A suíte continua compatível com `python -m unittest discover -s tests`.
- Marcadores aplicados automaticamente por `tests/conftest.py`: `integration` (toda chamada real ao Xano), `writes` (grava dados) e `concurrency` (corridas).
- Handlers que mostram carregamento são geradores (fazem `yield` antes de chamar o Xano). Nos testes, use `tests.event_runner.run_event(Handler, state, ...)`, que executa o handler como o Reflex e devolve o evento final; `tests/test_loading_states.py` garante que todo handler de submissão e de carga continue gerador.
- Os testes offline usam `httpx.MockTransport` e contratos estáticos sobre `xano/`; não precisam de rede.
- `tests/test_integration_xano.py` é opt-in: só chama o Xano com `XANO_API_BASE_URL` configurada **e** `XANO_TEST_ALLOW_WRITES=true` (suíte completa) ou `XANO_TEST_LIVE=true` (apenas leitura). Sem isso, cada teste é ignorado com o motivo, e um `pytest` comum nunca depende de rede, credenciais ou do limite de `429`.
- Credenciais por perfil: `XANO_TEST_GERENTE_EMAIL`/`_PASSWORD`, `XANO_TEST_VENDEDOR_*` e `XANO_TEST_MECANICO_*`. Perfis sem credenciais são ignorados individualmente.
- Os cenários que gravam dados (registro de entrada, documento duplicado, rollback, ciclo completo de OS com as rejeições da máquina de estados, e ciclo de itens com baixa, devolução, totais e cancelamento) exigem `XANO_TEST_ALLOW_WRITES=true`. Como entradas, OS encerradas e movimentações de estoque são imutáveis, rode-os em um branch ou workspace de testes. As OS abertas pelos testes são canceladas ao final, devolvendo as peças.
- `XANO_TEST_CONCURRENCY=true` (junto com as escritas) roda as corridas: duas OS disputando todo o saldo de um produto e uma inclusão simultânea ao cancelamento. Exige duas motos de cliente sem OS em aberto.
- A leitura pública do catálogo roda sem credenciais (com a integração ativada) e é ignorada, com aviso, enquanto a Change 8 não estiver publicada. O ciclo de reserva (`ALLOW_WRITES`) cria um modelo e uma unidade próprios e retira o modelo do catálogo ao final; a corrida de duas reservas da mesma unidade exige `XANO_TEST_CONCURRENCY`.
- O financeiro (Change 10) tem testes sem escrita (`VENDEDOR` e `MECANICO` recebem `403` no resumo e em `GET transacoes`; escrita manual `403` até para o `GERENTE`; período inválido `400`), o ciclo com escrita (conclusão gera um único lançamento visível no resumo; OS vazia e cancelada não geram) e a corrida de duas conclusões (`XANO_TEST_CONCURRENCY`).
- O balcão (Change 11) tem testes sem escrita (`MECANICO` recebe `403`; carrinho vazio, com produto repetido ou com mais de 30 itens recebe `400`), com escrita (consumidor final baixa o estoque e aparece no resumo; a mesma `chave_venda` devolve a mesma venda com uma única baixa; saldo insuficiente e preço alterado não gravam nada) e a disputa de duas vendas pelo saldo inteiro (`XANO_TEST_CONCURRENCY`).
- A venda (Change 9) tem um teste sem escrita (`MECANICO` recebe `403`, unidade inexistente `404`), o ciclo com escrita (venda sem placa, venda repetida, unidade reservada para outro cliente, segunda moto sem placa) e a corrida de duas vendas da mesma unidade (`XANO_TEST_CONCURRENCY`). Vendas são finais: unidades vendidas, motos de clientes e transações de teste ficam no banco.
- O workspace do Xano limita a taxa de requisições (`429` após cerca de 6 chamadas seguidas): a suíte completa com credenciais pode falhar de forma intermitente por isso.
- Os testes de cada Change exigem o respectivo push; antes dele, os endpoints novos respondem `404`.
