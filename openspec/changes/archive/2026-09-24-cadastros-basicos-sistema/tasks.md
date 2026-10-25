# Tarefas

## Decisões e contratos

- [x] Aprovar o significado e o formato de `produtos.codigo`.
- [x] Aprovar a unicidade de `produtos.codigo`.
- [x] Aprovar o modelo de desativação (`ativo` ou equivalente) para os cadastros.
- [x] Confirmar a matriz Xano final para escrita de `motos_clientes` por vendedor.
- [x] Comparar payloads reais dos endpoints com os DTOs planejados.

## Base compartilhada

- [x] Definir DTOs de leitura, criação e atualização para os cinco recursos.
- [x] Definir mensagens comuns para validação, duplicidade, `401`, `403` e falha de transporte.
- [x] Definir componente reutilizável de tabela com busca, paginação, loading e estado vazio.
- [x] Definir componente reutilizável de modal e feedback de mutação.
- [x] Definir predicados de autorização para exibição de ações no App Shell.

## Clientes

- [x] Implementar serviço e métodos Xano de clientes.
- [x] Implementar estado Reflex de listagem, busca, criação, edição e desativação.
- [x] Implementar tela de clientes no App Shell.
- [x] Implementar validações de nome, CPF/CNPJ, email e duplicidade.
- [x] Criar testes de DTO, serviço, estado e autorização.

## Motos de clientes

- [x] Implementar serviço e DTOs de `motos_clientes`.
- [x] Ajustar autorização Xano para escrita de vendedor e gerente.
- [x] Implementar seleção de cliente existente no formulário.
- [x] Implementar busca por cliente, modelo, placa e chassi.
- [x] Implementar validações e testes de unicidade de placa/chassi.

## Produtos e fornecedores

- [x] Aplicar no Xano o contrato aprovado para código e desativação.
- [x] Implementar serviços e DTOs de produtos e fornecedores.
- [x] Implementar telas de consulta e manutenção conforme a matriz.
- [x] Implementar validações de preço, estoque e CNPJ.
- [x] Criar testes de leitura para vendedor/mecânico e mutação somente para gerente.

## Funcionários

- [x] Implementar serviço e DTOs de funcionários.
- [x] Implementar tela de consulta e manutenção exclusiva do gerente.
- [x] Validar tipos `GERENTE`, `VENDEDOR` e `MECANICO`.
- [x] Garantir que o cadastro de funcionário não crie nem altere usuário Xano implicitamente.
- [x] Criar testes do CRUD e da autorização.

## Verificação

- [x] Executar testes unitários e de contrato.
- [x] Executar testes com os três perfis da matriz.
- [x] Executar `python -m py_compile` nos arquivos afetados.
- [x] Executar `reflex compile --dry`.
- [x] Validar todos os XanoScript alterados.
- [x] Validar os fluxos de tabela, busca, modal, toast e estados vazios por compilação e testes de estado.
- [x] Confirmar que não há acesso direto do Reflex ao banco.
- [x] Registrar resultados e limitações antes do Archive.

Nenhum arquivo de implementação deve ser alterado durante a etapa Propose.
