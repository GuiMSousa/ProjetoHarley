# Seed seguro do usuário gerente

Este diretório documenta o seed mínimo necessário para testes de autenticação. A
senha nunca deve ser gravada neste repositório.

## Procedimento

1. Criar ou selecionar um registro em `funcionarios` com `tipo = GERENTE`.
2. Criar um usuário em `user` com `role = admin` e `id_funcionario` apontando para
   o funcionário gerente.
3. Definir `email` e `password` por segredo/configuração do ambiente Xano.
4. Validar com `POST /auth/login` e `GET /auth/me`.

O ambiente de teste deve garantir pelo menos um usuário gerente ativo. Credenciais
reais, hashes e tokens não podem ser adicionados ao export versionado.