# Modelo de Domínio — HarleyDavidsonStore

Este documento especifica as entidades, atributos conceituais e relacionamentos que regem o sistema da concessionária e oficina.

---

## Entidades Principais

### Fornecedores
Representa as empresas parceiras que fornecem peças, produtos e motocicletas para reposição de estoque.
- **Atributos:** Identificador (`id_fornecedor`), Nome/Razão Social (`nome_fornecedor`), CNPJ (`cnpj`), Contato (`contato`).
- **Regras:** O CNPJ deve ser único no sistema.

### Produtos
Representa os itens físicos comercializados pela concessionária ou utilizados na oficina mecânica.
- **Atributos:** Identificador (`id_produto`), Nome (`nome_produto`), Descrição (`descricao`), Categoria (`categoria`), Quantidade em Estoque (`estoque_qtd`), Preço de Venda (`preco_venda`).
- **Regras:** O saldo em estoque e o preço de venda não podem ser negativos.

### Funcionarios
Representa os colaboradores da concessionária/oficina.
- **Atributos:** Identificador (`id_funcionario`), Nome (`nome_funcionario`), Cargo (`cargo`), Tipo (`tipo`), Contato (`contato`).
- **Regras:** O tipo deve ser obrigatoriamente um entre: `VENDEDOR`, `MECANICO` ou `GERENTE`.

### Clientes
Representa os proprietários de motocicletas ou compradores da loja.
- **Atributos:** Identificador (`id_cliente`), Nome (`nome_cliente`), CPF/CNPJ (`cpf_cnpj`), Telefone (`telefone`), Email (`email`), Endereço (`endereco`).
- **Regras:** CPF ou CNPJ deve ser único no sistema.

### Motos_Clientes
Representa as motocicletas vinculadas a determinado cliente para prestação de serviços de manutenção ou revisão.
- **Atributos:** Identificador (`id_moto_cliente`), Cliente Vinculado (`id_cliente`), Modelo (`modelo`), Placa (`placa`), Chassi (`chassi`).
- **Relacionamento:** Pertence a um **Cliente**.
- **Regras:** Placa e Chassi devem ser únicos no sistema.

### Entrada_Mercadoria & Itens_Compra_Estoque
Representa a nota/registro de compra efetuada junto a um fornecedor para abastecimento de estoque.
- **Atributos Entrada:** Identificador (`id_entrada`), Fornecedor (`id_fornecedor`), Data da Entrada (`data_entrada`), Valor Total (`valor_total`).
- **Atributos Itens da Compra:** Identificador (`id_item_compra`), Entrada (`id_entrada`), Produto (`id_produto`), Quantidade (`quantidade`), Valor Unitário (`valor_unitario`).
- **Relacionamentos:** Uma entrada possui um ou mais **Itens de Compra** e pertence a um **Fornecedor**.

### Ordens_Servico & Itens_Ordem_Servico
Representa o atendimento técnico prestado na oficina mecânica para a moto de um cliente.
- **Atributos OS:** Identificador (`id_os`), Moto do Cliente (`id_moto_cliente`), Funcionario Responsável (`id_funcionario`), Data de Abertura (`data_abertura`), Status (`status`).
- **Atributos Itens OS:** Identificador (`id_item_os`), Ordem de Serviço (`id_os`), Produto (`id_produto`), Quantidade (`quantidade`), Valor Total do Item (`valor_total_item`).
- **Relacionamentos:** Pertence a uma **Moto_Cliente**, é aberta por um **Funcionario** e é composta por vários **Produtos/Peças**.
- **Regras:** O status deve obrigatoriamente trafegar entre: `ABERTA`, `EM_ANDAMENTO`, `CONCLUIDA`, `CANCELADA`.

### Transacoes
Registra o fluxo financeiro de vendas e movimentações comerciais do estabelecimento.
- **Atributos:** Identificador (`id_transacao`), Tipo da Transação (`tipo_transacao`), Funcionário (`id_funcionario`), Cliente (`id_cliente`), Moto do Cliente (`id_moto_cliente`), Data (`data_transacao`), Valor Total (`valor_total`).
- **Regras:** O tipo de transação deve ser restrito aos valores: `MOTO`, `PECAS`, `BALCAO`, `COMPRA`, `ORDEM_SERVICO`.

---

## Visão Consolidada (`vw_resumo_operacoes`)
O domínio conta com um consolidado conceitual de operações que unifica as **Transações Comerciais** e as **Entradas de Mercadorias** para relatórios e consultas gerais de fluxo operacional.