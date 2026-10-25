# Tarefas

## Contrato e inventário

- [x] Listar todos os endpoints que recebem `id_funcionario` e separar autoria de responsável de negócio.
- [x] Confirmar o comportamento final para payloads que contenham `id_funcionario` adulterado.
- [x] Definir a resposta esperada para acesso direto proibido às rotas Reflex.
- [x] Confirmar todos os campos financeiros que devem ser estritamente positivos.

## Xano e segurança

- [x] Alterar `motos_clientes_id_PUT.xs` para usar `required_role: "VENDEDOR"`.
- [x] Criar ou reutilizar função para resolver o funcionário a partir de `$auth.id`.
- [x] Remover/ignorar `id_funcionario` de payloads de OS e transações.
- [x] Persistir autoria com o funcionário retornado do vínculo `user.id_funcionario`.
- [x] Alterar schemas financeiros para `min:0.01` onde aplicável.
- [x] Revisar inputs `dblink` para impedir sobrescrita dos campos de autoria.
- [x] Validar todos os XanoScript alterados.

## Guards Reflex

- [x] Criar helper de autorização por cargo para páginas protegidas.
- [x] Aplicar guard exclusivo de gerente em `/admin`.
- [x] Aplicar guard de gerente/mecânico em `/workshop`.
- [x] Redirecionar sessão ausente para `/login`.
- [x] Preservar sessão e exibir feedback para usuário sem permissão.
- [x] Testar a matriz de acesso sem depender dos links da sidebar.

## Loading e bloqueio de operações

- [x] Adicionar flags de carregamento de lista, salvamento e desativação ao estado de cadastros.
- [x] Bloquear botões durante chamadas HTTP.
- [x] Impedir reentrada no mesmo evento enquanto houver requisição pendente.
- [x] Exibir texto/indicador de progresso e manter feedback de erro.
- [x] Garantir limpeza das flags em sucesso e exceção.

## Testes

- [x] Criar testes para autorização de `PUT` e `PATCH` de motos de clientes.
- [x] Criar testes para autoria derivada do JWT em OS e transações.
- [x] Criar testes para rejeição de `id_funcionario` arbitrário.
- [x] Criar testes para valores financeiros zero, negativos e positivos.
- [x] Criar testes de guards por cargo e sessão ausente.
- [x] Criar testes de loading, bloqueio e prevenção de chamadas duplicadas.
- [x] Executar a suíte automatizada existente.
- [x] Executar `python -m py_compile`.
- [x] Executar `reflex compile --dry`.

## Documentação

- [x] Atualizar `docs/domain-model.md`.
- [x] Atualizar `docs/xano-api-client.md`.
- [x] Registrar a matriz final e o comportamento de autoria derivada do JWT.
- [x] Registrar limitações da integração real com Xano, se o ambiente continuar indisponível.

Nenhum arquivo de implementação deve ser alterado durante a etapa Propose.
