# Proposta: estabilização da autenticação e do cliente Xano

## Contexto

A fundação de autenticação, autorização e integração HTTP foi implementada na Change arquivada `autenticacao-identidade-design-system`. A aplicação já possui login, cookie JWT, restauração de sessão, shell autenticado e proteção dos endpoints de negócio.

Entretanto, a integração ainda não foi validada contra uma instância Xano configurada, o cliente Python expõe apenas métodos específicos para `motos`, e existem pontos de comportamento que podem produzir uma sessão inconsistente: o fluxo de login pode redirecionar para a área protegida após falha em `load_user`, o atributo `secure` do cookie está fixo para desenvolvimento e as respostas de autenticação precisam ser validadas explicitamente.

Esta Change 2.1 estabiliza essa fronteira antes da implementação dos cadastros de negócio.

## Problema

A aplicação precisa de um contrato HTTP genérico e verificável para consumir os endpoints Xano existentes, mantendo a distinção entre sessão inválida (`401`), sessão autenticada sem permissão (`403`), payload inválido e falha de transporte.

Também é necessário garantir que o payload do login e de `auth/me` corresponda ao contrato de identidade: o login deve retornar um token utilizável e `auth/me` deve retornar o usuário técnico e, quando aplicável, o funcionário vinculado. Usuários sem funcionário não devem acessar operações de negócio.

## Objetivo

Tornar a autenticação e o cliente Xano confiáveis para as próximas Changes, sem alterar regras operacionais de clientes, produtos, estoque, vendas ou ordens de serviço.

## Decisões de negócio

- O signup público será desativado.
- Apenas um `GERENTE` ou administrador autorizado poderá criar usuários.
- Todo usuário operacional deverá ser criado já vinculado a um funcionário.
- O `GERENTE` terá acesso irrestrito às rotas e funções de negócio.
- Operações transacionais, cálculos de totais e movimentações de estoque serão executados atomicamente no Xano.
- O frontend Reflex apenas consumirá os contratos e refletirá permissões; não será fonte de autorização.

## Escopo

- Refatorar `XanoClient` para manter chamadas HTTP genéricas, autenticadas e não autenticadas, reutilizáveis pelos 66 endpoints de negócio.
- Uniformizar o tratamento de `401`, `403`, `422`, demais erros HTTP e falhas de transporte.
- Validar a presença e o formato mínimo do token retornado pelo login.
- Validar o contrato de `auth/me`, incluindo usuário técnico e funcionário vinculado.
- Corrigir o fluxo de login para não redirecionar para `/` quando a sessão não puder ser validada.
- Tornar configurável por variável de ambiente o atributo `secure` do cookie JWT, preservando um valor adequado para desenvolvimento local.
- Melhorar as mensagens e notificações visuais de falha de autenticação na interface Reflex.
- Desativar o signup público no fluxo exposto pela aplicação.
- Adicionar testes unitários e de contrato para o cliente HTTP e o estado de autenticação.
- Executar validação contra uma instância Xano configurada quando as credenciais de ambiente estiverem disponíveis.

## Fora do escopo

- Criar telas ou serviços de clientes, produtos, fornecedores, motos, estoque, vendas ou ordens de serviço.
- Alterar a matriz detalhada de autorização dos endpoints de negócio, exceto garantir o acesso irrestrito do `GERENTE` conforme contrato existente.
- Implementar criação administrativa de usuários e telas de gestão de funcionários.
- Implementar renovação de JWT, recuperação de senha ou login por magic link.
- Alterar cálculos, transações ou movimentações de estoque do domínio.
- Migrar o banco para fora do Xano ou usar `docs/schema.sql` em runtime.
- Adicionar outro framework de frontend.

## Critérios de aceite

- Uma chamada autenticada sem token falha localmente com erro de autenticação, sem enviar uma requisição inválida ao Xano.
- Uma resposta `401` é convertida em `XanoAuthenticationError` e encerra a sessão local.
- Uma resposta `403` é convertida em `XanoPermissionError`, preserva a sessão e exibe uma notificação de acesso negado.
- Uma resposta `422` permanece distinguível como erro de validação.
- Falhas de transporte e respostas HTTP inesperadas não expõem token, senha ou hash nas mensagens e logs.
- O login só redireciona para `/` depois de o token e o usuário associado serem validados com sucesso.
- Uma sessão inválida ou um usuário sem funcionário permanece na tela de login, com mensagem compreensível.
- O cookie JWT usa `secure=False` por padrão em desenvolvimento e pode usar `secure=True` por configuração de ambiente.
- O signup público não aparece como rota ou ação disponível na aplicação.
- O payload de `auth/me` é validado sem aceitar senha ou hash como dados de identidade exibíveis.
- Os testes cobrem login válido, token ausente, `401`, `403`, payload inválido, usuário sem funcionário e falha de transporte.

## Dependências

- Instância Xano com o grupo de APIs configurado em `XANO_API_BASE_URL`.
- Endpoint de login retornando `authToken`.
- Endpoint `auth/me` retornando `{user, funcionario}` sem senha ou hash.
- Referência `user.id_funcionario` existente no schema Xano.
- Função Xano `Quick Start/enforce_role` preservando `GERENTE` como perfil superior.

## Resultado aplicado

- Cliente HTTP genérico com respostas Pydantic para autenticação, usuário e funcionário.
- Tratamento tipado de autenticação, autorização, validação, transporte e payload inesperado.
- Login Xano corrigido para carregar a senha apenas para verificação interna.
- Signup protegido para usuários autenticados com perfil `GERENTE` ou `admin` e vínculo obrigatório com funcionário.
- Cookie JWT configurável por `XANO_AUTH_COOKIE_SECURE`.
- Redirecionamento condicionado à validação bem-sucedida de `auth/me`.
- Alertas e toasts de falha na interface Reflex.
- 14 testes automatizados adicionados.

## Status

Aplicada e verificada em 2026-09-24. O teste de integração contra Xano real não foi executado porque não há `XANO_API_BASE_URL` e credenciais de ambiente disponíveis neste workspace.
