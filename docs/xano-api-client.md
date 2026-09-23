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

## Erros

- `XanoAuthenticationError`: token ausente, inválido ou expirado; a sessão deve ser limpa pela camada de autenticação.
- `XanoPermissionError`: token válido sem permissão; a sessão deve ser preservada.
- `XanoValidationError`: payload rejeitado pelo backend.
- `XanoError`: falha de transporte ou erro inesperado da API.

O cliente não interpreta payloads de domínio. Cada serviço futuro deve definir seus próprios tipos e endpoints sobre esta fronteira.
