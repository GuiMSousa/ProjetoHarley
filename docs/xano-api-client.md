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

## Erros

- `XanoAuthenticationError`: token ausente, inválido ou expirado; a sessão deve ser limpa pela camada de autenticação.
- `XanoPermissionError`: token válido sem permissão; a sessão deve ser preservada.
- `XanoValidationError`: payload rejeitado pelo backend.
- `XanoError`: falha de transporte ou erro inesperado da API.
- `XanoResponseError`: resposta HTTP bem-sucedida que não respeita o DTO esperado.

O cliente não interpreta payloads de domínio. Cada serviço futuro deve definir seus próprios tipos e endpoints sobre esta fronteira.

## Autoria operacional

Endpoints de OS e transações devem derivar `id_funcionario` do usuário autenticado no Xano: o backend resolve `$auth.id` para `user.id_funcionario` e persiste esse vínculo. Um `id_funcionario` enviado pelo frontend não é fonte de autoria e deve ser ignorado ou rejeitado pelo endpoint.

O frontend pode esconder ações incompatíveis com o cargo, mas a autorização final, a autoria e a integridade dos dados permanecem no Xano.
