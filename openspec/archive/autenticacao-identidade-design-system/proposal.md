# Proposta: autenticação, identidade, autorização e design system Harley-Davidson

## Problema

O backend Xano possui autenticação básica, mas os endpoints de negócio ainda não estão protegidos de forma uniforme. A função de autorização existente considera apenas os papéis técnicos `admin` e `member`, enquanto as operações do domínio dependem dos tipos de funcionário `GERENTE`, `VENDEDOR` e `MECANICO`. O endpoint `auth/me` também não retorna o funcionário associado ao usuário autenticado, e o login ainda envia dados sensíveis para o log de auditoria.

No frontend, o pacote `Projeto_HarleyStore` permanece no scaffold inicial do Reflex. Não existe tela de login, persistência de sessão, restauração após F5, layout autenticado, navegação por permissão ou tema visual compartilhado.

## Objetivo

Implementar a fundação de autenticação, identidade e autorização do sistema, proteger os endpoints de negócio e estabelecer o design system visual Harley-Davidson no Reflex para que as próximas Changes possam construir funcionalidades autenticadas de forma consistente.

## Resultado aplicado

- Endpoints de negócio protegidos e autorizados por cargo de funcionário.
- Logs de login e signup sem senha ou hash.
- `auth/me` retornando usuário e funcionário associado.
- Seed seguro de gerente via `Quick Start/seed_gerente`.
- Tema escuro Harley-Davidson centralizado.
- Login, cookie JWT, restauração de sessão, logout, shell, menus por perfil e rotas base implementados.

## Fora do escopo

- CRUD e regras operacionais de clientes, produtos, estoque, vendas ou OS.
- Integração contra uma instância Xano sem ambiente/credenciais configurados.

## Status

Aplicada e verificada em 2026-09-23. Arquivada após validação sintática XanoScript, compilação Python e `reflex compile --dry`.