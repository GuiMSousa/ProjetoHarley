# Change: definir-arquitetura-e-fundacao

## Problema

O projeto possui um frontend Reflex inicial, exports do Xano e documentação que ainda descreve SQL Server e tecnologias a definir. Também não existe um contrato explícito para o consumo HTTP do Xano, a gestão do JWT ou a relação entre a identidade autenticada e os funcionários do domínio.

## Objetivo

Estabelecer a fundação arquitetural oficial do sistema para que as próximas Changes possam entregar funcionalidades verticais sobre contratos estáveis:

- Xano será o backend oficial, responsável pela persistência, autenticação, autorização e APIs.
- `Projeto_HarleyStore/` será o pacote da aplicação Reflex.
- `xano/` será a fonte versionada dos schemas, funções e endpoints do backend.
- O Reflex consumirá o Xano através de um cliente HTTP centralizado, usando JWT sem expor credenciais no código.
- A identidade da tabela `user` será relacionada ao funcionário e aos cargos `GERENTE`, `VENDEDOR` e `MECANICO`.

## Escopo

- Atualizar documentação e configuração do OpenSpec para refletir Xano + Reflex.
- Padronizar referências ao pacote `Projeto_HarleyStore`.
- Converter `requirements.txt` para UTF-8.
- Documentar a organização da integração Xano.
- Definir o contrato arquitetural do cliente HTTP e do JWT.
- Definir o mapeamento entre `user` e `Funcionarios`.
- Preparar tarefas verificáveis para a implementação posterior da fundação.

## Fora do escopo

- Criar telas ou CRUD de clientes, produtos, fornecedores, funcionários, motos, entradas ou OS.
- Criar ou alterar endpoints operacionais do Xano.
- Implementar login, logout ou armazenamento de tokens nesta Change.
- Alterar regras de estoque, transações ou estados de OS.
- Migrar ou executar `docs/schema.sql`.
- Criar uma tabela de usuários duplicada no domínio.

## Resultado esperado

Ao final da Change, a arquitetura escolhida estará registrada, os caminhos e nomes estarão consistentes, e haverá um contrato suficiente para a próxima Change implementar autenticação e o shell autenticado do Reflex.
