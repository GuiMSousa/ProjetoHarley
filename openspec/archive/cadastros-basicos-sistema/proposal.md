# Proposta: cadastros básicos do sistema

## Contexto

A fundação Xano/Reflex, a autenticação e o cliente HTTP foram estabilizados nas Changes anteriores. O frontend ainda exibe apenas o shell autenticado e páginas placeholder, enquanto o backend já possui endpoints protegidos para clientes, motos de clientes, produtos, fornecedores e funcionários.

Esta Change 3 inicia as primeiras fatias verticais de negócio: cada cadastro deverá atravessar o contrato Xano, DTOs e serviços Python, estado Reflex, tela no App Shell, validações, controle de acesso e testes.

## Problema

A operação ainda não possui telas funcionais para manter os cadastros necessários à oficina e à concessionária. Sem clientes e motos vinculadas, a oficina não consegue iniciar o histórico de atendimento; sem produtos, fornecedores e funcionários, as próximas operações de estoque e ordens de serviço não têm dados de referência confiáveis.

Também existem diferenças entre a matriz de acesso desejada e os exports atuais do Xano, além de campos solicitados pela interface que ainda não existem no modelo persistido:

- `produtos` não possui atualmente um campo de código.
- Nenhuma das tabelas de cadastro possui campo de desativação/inativação.
- A escrita de `motos_clientes` está atualmente autorizada para `MECANICO`, mas a regra desta Change exige escrita para `VENDEDOR` e `GERENTE`.
- A criação/edição de `funcionarios`, fornecedores e produtos deve permanecer restrita ao gerente.

## Objetivo

Entregar cadastros básicos utilizáveis dentro do App Shell Harley-Davidson, com contratos de backend alinhados à matriz de acesso, validação duplicada no frontend e Xano, feedback de operação e testes suficientes para sustentar as próximas Changes de estoque e oficina.

## Escopo funcional

### Clientes

- DTOs de leitura, criação e atualização.
- Listagem com busca textual por nome, CPF/CNPJ ou contato.
- Criação e edição em modal.
- Validação de formato e unicidade de CPF/CNPJ.
- Desativação somente se o contrato Xano possuir um estado de ativo definido; a solução não deve apagar dados necessários ao histórico.

### Motocicletas de clientes

- DTOs de leitura, criação e atualização.
- Listagem com busca por placa, chassi, modelo ou cliente.
- Modal para vínculo obrigatório com cliente existente.
- Validação de placa e chassi únicos.
- Criação e edição autorizadas a gerente e vendedor conforme a matriz aprovada.
- Leitura disponível para gerente, vendedor e mecânico.

### Produtos e peças

- DTOs de leitura, criação e atualização.
- Listagem com busca por código, nome, categoria e descrição.
- Formulário com código, descrição, categoria, preço de venda e saldo de estoque.
- Validação de preço estritamente positivo e estoque não negativo.
- Leitura para todos os perfis; escrita e desativação para gerente.
- Inclusão do campo de código no contrato Xano somente após definir sua unicidade e formato.

### Fornecedores

- DTOs de leitura, criação e atualização.
- Listagem e busca por razão social, CNPJ e contato.
- Validação de CNPJ único.
- Escrita e desativação restritas ao gerente.

### Funcionários

- DTOs de leitura, criação e atualização.
- Listagem e busca por nome, cargo e tipo.
- Formulário com cargo, contato e tipo.
- Tipo limitado a `GERENTE`, `VENDEDOR` ou `MECANICO`.
- Leitura, escrita e desativação restritas ao gerente.
- Preservação da referência `user.id_funcionario`; esta Change não cria usuários de autenticação.

## Requisitos de interface e UX

- Todas as telas devem usar `app_shell`, sidebar, navbar, paleta e componentes do tema existente.
- Cada tela deve possuir tabela de dados com estado vazio, carregamento, erro, busca textual e paginação.
- Criação e edição devem ocorrer em modal com validação antes do envio.
- Ações devem respeitar o perfil atual e não apenas esconder erros do backend.
- Sucessos, falhas de validação, duplicidades, ausência de permissão e falhas de transporte devem gerar toast ou alerta visível.
- A interface não deve exibir IDs técnicos ou payloads brutos como substituto de informações legíveis.
- A paginação deve ser compatível com o contrato real do endpoint; se o Xano ainda retornar listas completas, a primeira versão deverá paginar a apresentação sem prometer paginação server-side.

## Matriz de acesso

| Recurso | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Clientes | CRUD completo | leitura e escrita | leitura |
| Motos de clientes | CRUD completo | leitura e escrita | leitura |
| Produtos/peças | CRUD completo | leitura | leitura |
| Fornecedores | CRUD completo | sem acesso | sem acesso |
| Funcionários | CRUD completo | sem acesso | sem acesso |

O Xano continua sendo a autoridade final. A matriz deve ser aplicada nos endpoints e refletida no frontend. O gerente técnico `admin`, conforme Change 2.1, mantém acesso superior quando o usuário estiver validamente vinculado.

## Alinhamentos de contrato Xano necessários

- Definir `produtos.codigo`, incluindo tipo, normalização e índice único, antes de implementar a tela que o exibe.
- Definir o modelo de desativação, preferencialmente um campo `ativo` ou equivalente, e seu comportamento nas listagens e relacionamentos. Até essa decisão, não implementar exclusão lógica no frontend como se já existisse.
- Alterar a autorização de `motos_clientes` para permitir escrita por `VENDEDOR` e `GERENTE`, mantendo leitura para os três perfis.
- Confirmar que endpoints de clientes, produtos, fornecedores e funcionários aceitam payloads e respostas compatíveis com os DTOs planejados.
- Garantir que duplicidades sejam rejeitadas atomicamente pelo Xano e mapeadas pelo cliente como erro de validação compreensível.

## Fora do escopo

- Entrada de mercadoria, itens de compra e atualização transacional de estoque.
- Venda de motos, venda de balcão e criação de transações financeiras.
- Ordens de serviço e itens de OS.
- Criação de usuários Xano, signup administrativo ou redefinição de senha.
- Histórico de serviços e dashboard operacional.
- Alteração do tema visual global já implementado.
- Acesso direto do Reflex ao banco ou uso de `docs/schema.sql` em runtime.
- Exclusão física de registros que já possuam relacionamentos de negócio.

## Critérios de aceite gerais

- Um usuário gerente consegue consultar, criar, editar e desativar registros nos cinco cadastros, respeitando as decisões de modelo para código e ativo.
- Um vendedor consegue consultar e manter clientes e motos de clientes, mas não consegue alterar produtos, fornecedores ou funcionários.
- Um mecânico consegue consultar clientes, motos de clientes e produtos, mas não consegue executar escrita.
- O Xano rejeita tentativas não autorizadas mesmo que a ação seja forjada fora do frontend.
- O frontend bloqueia ações incompatíveis com o perfil e apresenta a resposta `403` de forma compreensível.
- Duplicidades de CPF/CNPJ, placa, chassi e código de produto não criam registros parciais.
- Preço de produto menor ou igual a zero e estoque negativo são rejeitados antes ou durante o envio.
- O vínculo de uma moto exige cliente existente e válido.
- Todas as telas funcionam dentro do App Shell e mantêm estados de carregamento, vazio, erro e sucesso.
- A implementação possui testes de DTO, cliente HTTP, estado Reflex, autorização e fluxos principais de cada cadastro.

## Dependências

- Change 2.1 arquivada e cliente Xano autenticado.
- Endpoints Xano protegidos e contratos de `clientes`, `motos_clientes`, `produtos`, `fornecedores` e `funcionarios`.
- Definição aprovada para `produtos.codigo` e desativação.
- Usuário de teste para cada perfil da matriz.
- Dados de referência para clientes antes da criação de motos de clientes.

## Resultado aplicado

- Cinco cadastros foram integrados ao cliente Xano com DTOs Pydantic, listagem, criação, atualização e soft delete.
- O schema de produtos passou a suportar `codigo` alfanumérico único e todos os cinco cadastros passaram a possuir `ativo` com default verdadeiro.
- O App Shell recebeu rotas, busca, paginação client-side, modais, seleção de cliente para motos e feedback visual.
- A matriz de estado foi aplicada para gerente, vendedor e mecânico, com autorização final preservada no Xano.
- Foram adicionados 21 testes automatizados.

## Status

Aplicada e verificada em 2026-09-24. A integração contra uma instância Xano real não foi executada porque não há URL ou credenciais externas configuradas neste workspace.
