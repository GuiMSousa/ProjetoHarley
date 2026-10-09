# Especificação: cadastros básicos

Consolida o que a Change 3 (`cadastros-basicos-sistema`) entregou, com os ajustes posteriores: exclusão somente lógica (saneamento pós-Change 7) e placa opcional (Change 9).

## Requisito: recursos cadastrados

O sistema DEVE manter cinco cadastros, todos com o campo `ativo`: clientes (`nome_cliente`, `cpf_cnpj`, telefone, email, endereço), motos de clientes (cliente, `modelo`, `placa`, `chassi`), produtos e peças (`codigo`, nome, descrição, categoria, `estoque_qtd`, `preco_venda`), fornecedores (`nome_fornecedor`, `cnpj`, contato) e funcionários (`nome_funcionario`, `cargo`, `tipo`, contato).

## Requisito: identificadores únicos

`clientes.cpf_cnpj`, `fornecedores.cnpj`, `produtos.codigo` e `motos_clientes.chassi` DEVEM ser únicos no Xano (índice único). `motos_clientes.placa` DEVE ser única quando informada e PODE ser nula (moto 0 km vendida antes do emplacamento); placa em branco DEVE valer como ausente. `produtos.codigo` DEVE ser alfanumérico. Duplicidades DEVEM ser rejeitadas pelo Xano e exibidas como erro de validação legível.

### Cenário: CPF/CNPJ repetido

- **DADO** um cliente com CPF/CNPJ `12345678900`
- **QUANDO** outro cadastro informar o mesmo CPF/CNPJ
- **ENTÃO** o Xano DEVE rejeitar a gravação e a tela DEVE manter o formulário aberto com a mensagem

## Requisito: valores e saldo de produtos

`preco_venda` DEVE ser maior que zero. `estoque_qtd` DEVE ser maior ou igual a zero e só PODE ser informado na criação do produto; depois disso o saldo muda somente por movimentações de estoque (spec `estoque-entradas`). Edições de produto NÃO DEVEM aceitar `estoque_qtd`.

## Requisito: tipos de funcionário

`funcionarios.tipo` DEVE ser `GERENTE`, `VENDEDOR` ou `MECANICO`. O cadastro de funcionários NÃO DEVE criar usuários de autenticação; o vínculo `user.id_funcionario` é feito por `auth/signup` (spec `arquitetura-e-contratos`).

## Requisito: desativação lógica

Registros DEVEM ser desativados por `PATCH` com `ativo = false`; o `DELETE` físico responde `403` (spec `arquitetura-e-contratos`). Registros inativos DEVEM continuar legíveis no histórico (OS, entradas, vendas).

## Requisito: matriz de acesso

| Recurso | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Clientes | leitura, criação, edição e desativação | leitura, criação, edição e desativação | leitura |
| Motos de clientes | leitura, criação, edição e desativação | leitura, criação, edição e desativação | leitura |
| Produtos e peças | leitura, criação, edição e desativação | leitura | leitura |
| Fornecedores | leitura, criação, edição e desativação | sem acesso | sem acesso |
| Funcionários | leitura, criação, edição e desativação | sem acesso | sem acesso |

O Xano DEVE aplicar a matriz em cada endpoint (`enforce_role`); o Reflex DEVE espelhá-la nas rotas (`ROUTE_ROLES`) e esconder as ações que o perfil não pode executar.

## Requisito: interface dos cadastros

Cada cadastro DEVE ter tabela com busca, paginação, estado vazio, carregamento e erro; criação e edição DEVEM acontecer em modal, com validação local antes do envio, e todo resultado (sucesso, duplicidade, permissão, falha de comunicação) DEVE gerar notificação ou alerta visível.
