# Especificação: arquitetura e contratos

## Requisito: estrutura oficial

O sistema DEVE utilizar `Projeto_HarleyStore/` como pacote da aplicação Reflex e `xano/` como diretório versionado dos exports do backend.

### Cenário: referências estruturais

- **DADO** o código e a documentação do projeto
- **QUANDO** uma referência ao pacote ou aos exports for criada
- **ENTÃO** o pacote DEVE ser `Projeto_HarleyStore` e os exports DEVEM apontar para `xano/`

## Requisito: entidades de motocicletas

`motos_clientes` DEVE representar veículos pertencentes a clientes e utilizados pela oficina. `motos` DEVE representar motocicletas mantidas no estoque da loja para venda.

### Cenário: separação de finalidade

- **DADO** um veículo usado no histórico de serviços
- **ENTÃO** ele DEVE referenciar `motos_clientes`
- **E** uma motocicleta mantida para venda DEVE referenciar `motos`

## Requisito: valores positivos

O backend DEVE rejeitar `preco_venda` e `valor_unitario` menores ou iguais a zero. Quantidades de itens também DEVEM ser maiores que zero, enquanto `estoque_qtd` DEVE ser maior ou igual a zero.

### Cenário: valor inválido

- **DADO** um payload com `preco_venda <= 0` ou `valor_unitario <= 0`
- **QUANDO** o payload for validado pelo Xano
- **ENTÃO** a operação DEVE ser rejeitada como inválida

## Requisito: criação de motocicleta de estoque

O endpoint `POST motos` DEVE persistir todos os campos de domínio recebidos no payload (`clientes_id`, `marca` e `modelo`) e o timestamp de criação.

### Cenário: payload de moto

- **DADO** um payload válido para uma motocicleta de estoque
- **QUANDO** o endpoint `POST motos` for executado
- **ENTÃO** os campos recebidos DEVEM aparecer no registro criado

## Requisito: vínculo de identidade

A tabela `user` DEVE possuir o campo opcional `id_funcionario` como referência a `funcionarios.id`.

### Cenário: usuário vinculado

- **DADO** um usuário com `id_funcionario` preenchido
- **ENTÃO** o valor DEVE identificar um registro existente em `funcionarios`
- **E** o campo `user.role` DEVE continuar sendo tratado como papel técnico separado do tipo do funcionário