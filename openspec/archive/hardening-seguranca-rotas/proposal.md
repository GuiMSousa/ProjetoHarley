# Proposta: correção de inconsistências, hardening de segurança e blindagem de rotas

## Contexto

As Changes anteriores estabeleceram a autenticação JWT, a autorização por funcionário, o cliente HTTP tipado e os cinco cadastros básicos. A exploração posterior identificou inconsistências que precisam ser corrigidas antes da implementação de entradas de estoque, ordens de serviço e vendas.

Os principais pontos são:

- O endpoint `PUT motos_clientes/{id}` ainda exige `MECANICO`, enquanto o `PATCH` está alinhado à regra aprovada para `VENDEDOR` e `GERENTE`.
- Alguns endpoints aceitam `id_funcionario` no payload, permitindo que o cliente tente declarar outro funcionário para a operação.
- Campos financeiros de entradas, transações e itens de OS ainda aceitam zero.
- As rotas `/admin` e `/workshop` dependem principalmente da navegação condicional; não há guard explícito por cargo na entrada direta da URL.
- Os estados Reflex de listagem e mutação não possuem loading dedicado nem bloqueio consistente contra chamadas duplicadas.
- A documentação de domínio e integração não reflete integralmente os DTOs atuais e o soft delete.

## Problema

A aplicação pode apresentar uma permissão diferente entre métodos HTTP, registrar operações em nome de um funcionário informado pelo cliente, aceitar valores financeiros inválidos ou renderizar páginas protegidas para usuários que não possuem o cargo correspondente.

Essas falhas aumentam o risco de inconsistência de auditoria e tornam inseguro iniciar fluxos transacionais sobre estoque, OS e vendas.

## Objetivo

Corrigir os contratos de autorização e integridade, reforçar a proteção das rotas Reflex, impedir chamadas duplicadas durante operações assíncronas e alinhar a documentação e os testes ao estado real do sistema.

## Decisões de segurança

- A identidade do funcionário operacional será derivada do usuário autenticado no Xano, a partir do vínculo `user.id_funcionario` resolvido por `$auth.id`.
- `id_funcionario` enviado pelo cliente não será usado para atribuir autoria da operação. O campo será removido do input público quando possível ou ignorado/rejeitado pelo endpoint.
- O gerente e o usuário técnico `admin` autorizado continuam superiores na matriz de acesso.
- O frontend não é fonte de autorização; os guards melhoram a experiência e o Xano permanece a autoridade final.
- Valores financeiros sujeitos a esta Change serão estritamente maiores que zero (`> 0`).

## Escopo

### Xano

- Alterar `xano/api/harley/motos_clientes/motos_clientes_id_PUT.xs` para usar a mesma regra de autorização do `PATCH`, permitindo `VENDEDOR` e `GERENTE` conforme a matriz vigente.
- Revisar endpoints que recebem `id_funcionario`, incluindo OS e transações, para resolver o funcionário autenticado a partir do usuário do JWT.
- Garantir que o valor de autoria persistido não possa ser escolhido pelo payload.
- Alterar os schemas financeiros necessários para rejeitar valores menores ou iguais a zero, incluindo `entrada_mercadoria.valor_total`, `transacoes.valor_total` e `itens_ordem_servico.valor_total_item`.
- Revisar outros campos de preço/valor relacionados para manter a mesma regra do domínio.
- Validar os exports XanoScript alterados.

### Reflex

- Criar guard explícito para `/admin`, permitido somente a `GERENTE`.
- Criar guard explícito para `/workshop`, permitido a `GERENTE` e `MECANICO`.
- Redirecionar usuários não autenticados para `/login` e usuários autenticados sem cargo compatível para uma rota segura com notificação de acesso negado.
- Adicionar estado de carregamento para carregamento de listas, criação, edição e desativação dos cadastros.
- Desabilitar botões e impedir eventos duplicados enquanto uma operação estiver pendente.
- Preservar tratamento visual de erros `401`, `403`, validação e transporte.

### Testes e documentação

- Criar testes de contrato para autorização de `PUT`/`PATCH` e derivação de funcionário pelo JWT.
- Criar testes dos limites financeiros (`0`, negativos e positivos).
- Criar testes de guard de rota e loading/bloqueio de mutações.
- Atualizar [docs/domain-model.md](../../docs/domain-model.md) com `ativo`, `codigo`, soft delete e regras financeiras atuais.
- Atualizar [docs/xano-api-client.md](../../docs/xano-api-client.md) com DTOs tipados, métodos de cadastro e comportamento de erros.

## Fora do escopo

- Implementar entrada de mercadorias ou atualização atômica de estoque.
- Implementar ordens de serviço, itens de OS ou transições de status.
- Implementar vendas, balcão, transações derivadas ou dashboard.
- Criar tela administrativa de usuários Xano.
- Alterar a matriz de negócio além do alinhamento de `PUT motos_clientes` e da autoria derivada do JWT.
- Migrar o banco para fora do Xano.
- Adicionar um novo framework frontend.

## Critérios de aceite

- `PUT motos_clientes/{id}` e `PATCH motos_clientes/{id}` aplicam a mesma matriz para vendedor e gerente.
- Um payload com `id_funcionario` diferente do funcionário autenticado não altera a autoria persistida e é rejeitado ou ignorado conforme o contrato definido.
- Operações que não recebem `id_funcionario` explicitamente persistem o funcionário resolvido a partir de `user.id_funcionario`.
- `valor_total`, `valor_total_item` e demais campos financeiros cobertos rejeitam `0` e valores negativos no Xano e nos DTOs correspondentes.
- Acesso direto de vendedor ou mecânico a `/admin` não renderiza a página administrativa.
- Acesso direto de vendedor a `/workshop` não renderiza a página de oficina.
- Usuário não autenticado é redirecionado para `/login`.
- Botões de salvar, editar e desativar ficam bloqueados durante a requisição e não geram chamadas duplicadas.
- A suíte automatizada cobre os casos positivos, negativos, `401`, `403` e payload adulterado.
- Python, Reflex e todos os XanoScript alterados são validados antes do Archive.

## Dependências

- Changes de autenticação e cadastros arquivadas.
- Vínculo `user.id_funcionario` disponível no schema Xano.
- `Quick Start/enforce_role` funcionando como autoridade de cargo.
- Cliente Xano tipado em [Projeto_HarleyStore/services/xano_client.py](../../Projeto_HarleyStore/services/xano_client.py).
- Ambiente de testes com perfis gerente, vendedor e mecânico, preferencialmente contra Xano real para validar o contrato final.

## Resultado aplicado

- `PUT motos_clientes/{id}` foi alinhado ao `PATCH` para vendedor e gerente.
- OS e transações passaram a derivar `id_funcionario` de `user.id_funcionario` resolvido pelo usuário autenticado.
- Valores financeiros cobertos passaram a exigir `> 0` nos schemas Xano.
- `/admin` e `/workshop` receberam guards explícitos por cargo e restauração de sessão na entrada direta.
- Cadastros receberam flags de loading, prevenção de reentrada e botões desabilitados durante requisições.
- Documentação de domínio e cliente Xano foi atualizada.
- A suíte passou a conter 26 testes automatizados.

## Status

Aplicada e verificada em 2026-09-24. A integração contra uma instância Xano real não foi executada porque não há URL ou credenciais externas configuradas neste workspace.
