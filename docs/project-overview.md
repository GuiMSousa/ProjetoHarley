# Project Overview — HarleyDavidsonStore

## 1. Visão Geral
O **HarleyDavidsonStore** é um sistema integrado de gestão voltado para concessionárias e oficinas mecânicas especializadas em motocicletas. Ele centraliza o controle de estoque de peças e veículos, cadastros de clientes, histórico de faturamento/transações, além do gerenciamento completo do fluxo de ordens de serviço (OS) da oficina mecânica.

## 2. Problema
Concessionárias e oficinas de grande porte frequentemente enfrentam descontrole no fluxo de peças, falta de rastreabilidade de serviços prestados por moto/cliente e ruídos no acompanhamento de transações financeiras (vendas diretas vs. serviços). A falta de um domínio unificado resulta em divergência de estoque e insatisfação do cliente.

## 3. Objetivos
- Unificar o controle de vendas no balcão, vendas de motocicletas e prestação de serviços mecânicos.
- Garantir a rastreabilidade total de histórico das motos dos clientes em relação aos serviços realizados e peças aplicadas.
- Manter controle rígido de movimentação de estoque (compras de fornecedores x saídas por vendas ou OS).
- Oferecer uma visão consolidada das operações financeiras e entradas de mercadorias.

## 4. Público-Alvo / Usuários
- **Vendedores:** Responsáveis por transações de vendas no balcão e negociações.
- **Mecânicos:** Responsáveis pela execução dos serviços e alocação de itens nas Ordens de Serviço.
- **Gerentes:** Responsáveis pelo acompanhamento global, aprovações, gestão de fornecedores e controle financeiro.
- **Clientes:** Proprietários das motocicletas cadastradas no sistema.

## 5. Escopo
- Gestão de Clientes e suas respectivas motocicletas (Placa, Chassi, Modelo).
- Gestão de Fornecedores e Entrada de Mercadorias (composição do estoque).
- Gestão do Catálogo de Produtos e Peças com saldo de estoque e preço de venda.
- Gestão do Corpo de Funcionários e suas tipologias/cargos.
- Gerenciamento do ciclo de vida das Ordens de Serviço e seus itens.
- Registro de Transações financeiras unificadas e visão consolidada das operações.

## 6. Principais Funcionalidades
- Cadastro e consulta de fornecedores, produtos, clientes, funcionários e motocicletas.
- Registro de entrada de mercadorias atualizando o valor unitário e total.
- Abertura, troca de status (ABERTA, EM_ANDAMENTO, CONCLUIDA, CANCELADA) e fechamento de Ordens de Serviço.
- Associação de itens (produtos/peças) e quantidades a uma Ordem de Serviço.
- Lançamento de transações comerciais categorizadas (`MOTO`, `PECAS`, `BALCAO`, `COMPRA`, `ORDEM_SERVICO`).
- Consulta consolidada das operações registradas no sistema.

## 7. Requisitos e Restrições Importantes
- Unicidade obrigatória para identificadores fiscais e físicos: CNPJ de fornecedores, CPF/CNPJ de clientes, Placa e Chassi das motos.
- O estoque do produto não pode ser negativo (`estoque_qtd >= 0`).
- Preços e quantidades de itens devem ser valores estritamente positivos (`> 0`).
- Tipos de funcionários restritos ao domínio: `VENDEDOR`, `MECANICO` ou `GERENTE`.

## 8. Arquitetura Tecnológica
- **Backend / API oficial:** Xano, incluindo persistência, autenticação, autorização e regras de negócio expostas por API.
- **Frontend:** Reflex, no pacote `Projeto_HarleyStore`, consumindo os endpoints do Xano por cliente HTTP.
- **Banco de dados:** Gerenciado pelo Xano. O arquivo `docs/schema.sql` permanece como referência histórica/conceitual até ser substituído por uma especificação equivalente do Xano.

## 9. Princípios de Desenvolvimento
- As regras de integridade do banco (Foreign Keys, Uniques e Checks) devem ser sempre espelhadas nas validações das camadas de aplicação.
- A integridade do estoque deve ser priorizada durante a baixa via OS ou Vendas no Balcão.
- Mudanças devem ser executadas utilizando o OpenSpec de forma incremental.

## 10. Fonte de Verdade e Documentação
- Os exports e contratos do Xano em `xano/`, junto com `docs/domain-model.md`, são a fonte de verdade da aplicação.
- O arquivo `docs/schema.sql` não é executado pela aplicação e deve ser tratado apenas como referência legada durante a migração conceitual para o Xano.