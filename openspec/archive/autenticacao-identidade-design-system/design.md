# Design: autenticação, identidade e shell Harley-Davidson

## Backend Xano

Todos os endpoints de `xano/api/harley/` usam autenticação de usuário e chamam `Quick Start/enforce_role` antes da operação de negócio. A função consulta `user.id_funcionario`, carrega `funcionarios.tipo` e permite `GERENTE` como perfil administrativo superior. `VENDEDOR` e `MECANICO` recebem somente os recursos previstos na matriz da proposta.

O login e o signup registram somente identificadores e metadados não sensíveis. `auth/me` retorna `{user, funcionario}` e nunca inclui senha. O seed `Quick Start/seed_gerente` recebe email, senha e funcionário gerente por input de execução, sem credenciais versionadas.

## Estado Reflex

`AuthState` mantém o JWT em `rx.Cookie`, o perfil carregado e o estado de erro. O cookie expira em 24 horas, alinhado ao token Xano, e é enviado somente pelo cliente HTTP no cabeçalho Bearer. `401` limpa a sessão e redireciona para login; `403` preserva a sessão e apresenta toast.

## Tema e shell

`styles/theme.py` concentra a paleta preta/grafite, laranja de ação, bordas, espaçamento e tema escuro. O shell possui sidebar, navbar, identidade do funcionário e logout. Menus administrativos e de oficina são condicionais ao cargo.

## Rotas

- `/login`: acesso público.
- `/`: dashboard autenticado.
- `/admin`: shell autenticado para área gerencial.
- `/workshop`: shell autenticado para área de oficina.

As páginas de negócio continuam placeholders desta Change; CRUD e regras operacionais serão implementados em Changes posteriores.