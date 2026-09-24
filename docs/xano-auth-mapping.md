# Mapeamento de Identidade Xano

## Responsabilidades

- `user` é a identidade técnica usada pelo Auth do Xano.
- `Funcionarios` é a entidade de domínio usada nas operações da concessionária.
- O Reflex recebe o JWT do Xano e envia o token no cabeçalho `Authorization` nas chamadas autenticadas.

## Relação

Cada usuário autorizado a acessar operações de negócio deve possuir um vínculo explícito com um funcionário. O vínculo não deve ser inferido por nome, e-mail ou papel técnico.

O vínculo físico adotado é a referência opcional `user.id_funcionario -> funcionarios.id`.
Usuários técnicos podem existir sem vínculo durante a administração inicial, mas não
podem acessar operações de negócio enquanto o vínculo não estiver preenchido.

No export Xano, `user.id_funcionario` é uma referência à tabela `funcionarios`. O campo
identifica o funcionário de domínio associado ao usuário autenticado; ele não substitui
o `user.role` técnico nem deve ser inferido por nome ou email.

## Cargos de domínio

| Campo | Valores válidos |
| --- | --- |
| `Funcionarios.tipo` | `GERENTE`, `VENDEDOR`, `MECANICO` |
| `user.role` | `admin`, `member` |

`user.role` é um papel técnico de compatibilidade e não substitui `Funcionarios.tipo`. As permissões por operação serão definidas na Change de autenticação.

## Regras de segurança

- Usuários sem funcionário vinculado não acessam operações de negócio.
- O backend Xano deve validar autenticação e autorização; o frontend apenas reflete as permissões.
- Tokens, senhas e hashes não devem aparecer em logs ou metadados de auditoria.
- Resposta `401` encerra a sessão local; resposta `403` mantém a sessão e informa falta de permissão.
