# Design: estabilização da autenticação e do cliente Xano

## Princípios

- `XanoClient` continua sendo a única fronteira HTTP entre Reflex e Xano.
- O cliente não deve conhecer regras de telas ou domínio além dos contratos de autenticação já necessários.
- O backend Xano permanece responsável por autenticação, autorização, validação e integridade.
- Tokens, senhas e hashes não podem aparecer em logs, mensagens de erro ou estado renderizado.

## Cliente HTTP

`XanoClient.request` será a operação genérica para os métodos HTTP necessários pelos 66 endpoints. Os métodos auxiliares `get`, `post`, `patch` e `delete` devem delegar a ela, mantendo:

- URL base carregada de `XANO_API_BASE_URL`;
- cabeçalho `Authorization: Bearer <JWT>` somente em chamadas autenticadas;
- suporte a payload JSON, parâmetros e respostas sem conteúdo;
- fechamento consistente do cliente HTTP;
- erros tipados por categoria.

A categorização mínima será:

| Situação | Erro | Comportamento da sessão |
| --- | --- | --- |
| Token ausente, expirado ou rejeitado | `XanoAuthenticationError` | Encerrar sessão |
| Token válido sem autorização | `XanoPermissionError` | Preservar sessão e notificar |
| Payload rejeitado | `XanoValidationError` | Preservar sessão e informar erro |
| Transporte ou status inesperado | `XanoError` | Preservar sessão e informar indisponibilidade |

Mensagens vindas do Xano devem ser normalizadas antes de serem apresentadas. Nenhuma mensagem poderá incluir o cabeçalho de autorização ou credenciais.

## Contratos de autenticação

O método `login` deverá validar que a resposta seja um objeto e contenha `authToken` não vazio. Campos auxiliares, como `user_id`, poderão ser preservados no retorno, mas não substituem a validação posterior do usuário.

O método `current_user` deverá validar o formato mínimo:

```text
{
  "user": {
    "id": ..., 
    "name": ..., 
    "email": ...
  },
  "funcionario": {
    "id": ...,
    "nome_funcionario": ...,
    "tipo": "GERENTE|VENDEDOR|MECANICO"
  }
}
```

A implementação deve tolerar campos opcionais não relevantes, mas deve rejeitar respostas que não permitam determinar se o usuário está vinculado a um funcionário. O payload retornado não deve incluir senha ou hash no modelo exposto ao Reflex.

## Estado Reflex

O fluxo de login será dividido conceitualmente em três passos:

1. Validar os campos informados localmente.
2. Obter e armazenar temporariamente o token retornado pelo Xano.
3. Validar o token com `auth/me` antes de redirecionar.

Se o terceiro passo falhar, o token deve ser limpo, `is_authenticated` deve permanecer falso e o usuário deve continuar em `/login` com uma mensagem acionável.

`restore_session` deve aplicar a mesma regra: uma sessão existente só é considerada autenticada depois de `auth/me` retornar um funcionário válido.

O atributo `secure` do `rx.Cookie` deve ser derivado de uma configuração de ambiente explícita, por exemplo `XANO_AUTH_COOKIE_SECURE`, com valor padrão seguro para o cenário local documentado. A conversão deve aceitar valores booleanos textuais sem transformar qualquer valor arbitrário em verdadeiro por engano.

## Interface

A tela de login deve:

- mostrar erro de credenciais inválidas sem expor detalhes sensíveis;
- mostrar indisponibilidade do Xano separadamente de falta de permissão;
- mostrar confirmação visual de sessão expirada;
- impedir ações repetidas enquanto o login estiver em andamento;
- não exibir o token nem payload bruto da API.

O signup público não terá rota, link ou ação visível no Reflex. A criação administrativa de usuários ficará para uma Change própria.

## Escopo de testes

- Testes do cliente com transporte HTTP simulado para sucesso, token ausente, `401`, `403`, `422`, status inesperado e falha de rede.
- Testes de validação do payload de login e `auth/me`.
- Testes do `AuthState` para sucesso, sessão inválida, usuário sem funcionário e erro de permissão.
- Teste da configuração `XANO_AUTH_COOKIE_SECURE` para desenvolvimento e produção.
- Teste de compilação Python e `reflex compile --dry`.
- Validação manual ou de integração contra Xano quando `XANO_API_BASE_URL` estiver configurada.
