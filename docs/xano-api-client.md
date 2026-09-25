# Cliente HTTP do Xano

O Reflex acessa o backend somente através de `Projeto_HarleyStore.services.xano_client.XanoClient`.

## Configuração

Defina `XANO_API_BASE_URL` no ambiente de execução. O valor deve conter a URL base do grupo de APIs do Xano e não deve ser commitado como segredo. O arquivo `.env.example` mostra o formato esperado.

## Autenticação

A instância autenticada recebe o JWT através do argumento `token`. O cliente envia o cabeçalho:

```text
Authorization: Bearer <JWT>
```

O cliente não persiste tokens, não os registra em logs e não os envia em query strings. A Change de autenticação deverá decidir onde o estado da sessão será mantido pelo Reflex.

## DTOs e recursos

O cliente usa modelos Pydantic em `Projeto_HarleyStore.services.cadastros` para validar os recursos:

- `Cliente` / `ClienteCreate` / `ClienteUpdate`;
- `MotoCliente` / `MotoClienteCreate` / `MotoClienteUpdate`;
- `Produto` / `ProdutoCreate` / `ProdutoUpdate`;
- `Fornecedor` / `FornecedorCreate` / `FornecedorUpdate`;
- `Funcionario` / `FuncionarioCreate` / `FuncionarioUpdate`.

`Produto.codigo` é alfanumérico e único. Os cinco cadastros possuem `ativo`, usado para soft delete. A desativação chama `PATCH` com `ativo = false`; o cliente não deve usar `DELETE` físico para esses recursos.

`Produto.preco_venda` e demais valores financeiros usam validação estrita `> 0`. Quantidades de itens usam `> 0` e saldos de estoque usam `>= 0`.

O `XanoClient` oferece métodos tipados de listagem, criação, atualização e desativação para esses recursos, além da operação HTTP genérica.

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

## Erros

- `XanoAuthenticationError`: token ausente, inválido ou expirado; a sessão deve ser limpa pela camada de autenticação.
- `XanoPermissionError`: token válido sem permissão; a sessão deve ser preservada.
- `XanoValidationError`: payload rejeitado pelo backend (`400` de `precondition` com `inputerror`, ou `422`). Quando o corpo traz um campo `message` textual com até 200 caracteres, essa mensagem de negócio vira o texto da exceção (ex.: "Fornecedor inativo ou inexistente."); caso contrário, usa-se uma mensagem genérica. Nenhum outro campo do corpo é propagado.
- `XanoError`: falha de transporte ou erro inesperado da API.
- `XanoResponseError`: resposta HTTP bem-sucedida que não respeita o DTO esperado.

O cliente não interpreta payloads de domínio. Cada serviço futuro deve definir seus próprios tipos e endpoints sobre esta fronteira.

## Autoria operacional

Endpoints de OS e transações devem derivar `id_funcionario` do usuário autenticado no Xano: o backend resolve `$auth.id` para `user.id_funcionario` e persiste esse vínculo. Um `id_funcionario` enviado pelo frontend não é fonte de autoria e deve ser ignorado ou rejeitado pelo endpoint.

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

No Reflex, `ROUTE_ROLES` em `Projeto_HarleyStore/auth.py` espelha essa matriz por rota e alimenta o guard `guarded_page` e os links da sidebar. As rotas protegidas restauram a sessão no `on_load` antes de carregar dados.
