# Design: hardening de segurança e rotas

## Autoria derivada do JWT

O token Xano identifica o usuário técnico por `$auth.id`. O endpoint ou função de negócio deverá:

1. carregar `user` pelo ID autenticado;
2. validar que `user.id_funcionario` está preenchido;
3. carregar o registro de `funcionarios` vinculado;
4. usar esse funcionário como autor da operação;
5. ignorar ou rejeitar qualquer `id_funcionario` recebido no corpo.

A implementação não deve confiar em nome, email, cargo informado pelo frontend ou ID arbitrário. Quando uma operação permitir atuação sobre outro funcionário como responsável, isso deverá ser um requisito separado e autorizado explicitamente; não faz parte desta Change.

Os campos de autoria devem ser definidos pelo stack Xano, não por `dblink` aberto ao cliente. Os endpoints de OS e transações devem ser revisados primeiro por terem impacto direto em auditoria.

## Matriz de autorização

- `PUT motos_clientes/{id}` usará `required_role: "VENDEDOR"`, permitindo vendedor e gerente pela função `enforce_role`.
- `/admin` aceitará somente `GERENTE`.
- `/workshop` aceitará `GERENTE` e `MECANICO`.
- O perfil técnico `admin` continua superior no backend, mas o guard de frontend deve utilizar o cargo de domínio carregado em `AuthState` quando houver vínculo.

Os guards devem ser pequenos e reutilizáveis. Uma página protegida deverá decidir entre conteúdo, redirect para login ou redirect/toast de acesso negado sem depender da sidebar.

## Valores financeiros

Os schemas Xano devem usar limites estritos:

- `entrada_mercadoria.valor_total`: `min:0.01`, se permanecer no modelo.
- `transacoes.valor_total`: `min:0.01`.
- `itens_ordem_servico.valor_total_item`: `min:0.01`.
- preços e valores unitários existentes permanecem com `min:0.01`.

Os DTOs Python equivalentes devem usar `Decimal` com `gt=0`. Quantidades de itens continuam com `min:1`; estoque continua com `min:0`.

A Change apenas endurece os limites. Ela não define ainda como totais serão calculados atomicamente nem qual operação de origem cria uma transação.

## Loading e idempotência de interface

Os estados de cadastro terão flags separadas para:

- carregamento da lista;
- salvamento de formulário;
- desativação;
- erro da última operação.

Cada evento de mutação deverá:

- retornar imediatamente se a mesma operação já estiver em andamento;
- definir a flag antes da primeira chamada HTTP;
- limpar a flag em `finally`;
- atualizar a lista somente após sucesso;
- manter os dados e exibir erro em caso de falha.

A UI usará `disabled` e texto de progresso no botão. O bloqueio visual é apenas uma camada de ergonomia; duplicidade e autorização devem continuar protegidas no backend.

## Documentação

[docs/domain-model.md](../../docs/domain-model.md) deve refletir:

- `ativo` nos cadastros;
- `produtos.codigo` e sua unicidade;
- soft delete sem remoção física;
- limites financeiros estritos;
- autoria operacional derivada do funcionário vinculado.

[docs/xano-api-client.md](../../docs/xano-api-client.md) deve refletir:

- DTOs Pydantic por recurso;
- métodos de listagem, criação, atualização e desativação;
- erros de resposta tipados;
- ausência de confiança em `id_funcionario` vindo do cliente.

## Verificação

- Testes unitários dos helpers de guard e flags de loading.
- Testes de contrato XanoScript para `required_role` e payload adulterado.
- Testes de DTO para valores zero/negativos.
- `python -m unittest discover -s tests -v` ou runner adotado pelo projeto.
- `python -m py_compile`.
- `reflex compile --dry`.
- Validação dos exports XanoScript alterados.
- Integração real opcional quando `XANO_API_BASE_URL` e perfis de teste estiverem disponíveis.
