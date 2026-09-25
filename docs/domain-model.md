# Modelo de Domínio — HarleyDavidsonStore

Este documento especifica as entidades, atributos conceituais e relacionamentos que regem o sistema da concessionária e oficina.

---

## Entidades Principais

### Fornecedores
Representa as empresas parceiras que fornecem peças, produtos e motocicletas para reposição de estoque.
- **Atributos:** Identificador (`id_fornecedor`), Nome/Razão Social (`nome_fornecedor`), CNPJ (`cnpj`), Contato (`contato`), Ativo (`ativo`).
- **Regras:** O CNPJ deve ser único no sistema.
- **Ciclo de vida:** `ativo = false` representa soft delete; o registro não deve ser removido fisicamente.

### Produtos
Representa os itens físicos comercializados pela concessionária ou utilizados na oficina mecânica.
- **Atributos:** Identificador (`id_produto`), Código (`codigo`), Nome (`nome_produto`), Descrição (`descricao`), Categoria (`categoria`), Quantidade em Estoque (`estoque_qtd`), Preço de Venda (`preco_venda`), Ativo (`ativo`).
- **Regras:** O saldo em estoque deve ser maior ou igual a zero (`estoque_qtd >= 0`) e o preço de venda deve ser estritamente positivo (`preco_venda > 0`).
- **Regras:** `codigo` deve ser alfanumérico e único; desativação usa soft delete.
- **Saldo:** `estoque_qtd` é informado apenas na criação (saldo inicial de implantação). Depois disso, só muda por movimentações de estoque; `PUT`/`PATCH produtos/{id}` ignoram o campo.

### Funcionarios
Representa os colaboradores da concessionária/oficina.
- **Atributos:** Identificador (`id_funcionario`), Nome (`nome_funcionario`), Cargo (`cargo`), Tipo (`tipo`), Contato (`contato`), Ativo (`ativo`).
- **Regras:** O tipo deve ser obrigatoriamente um entre: `VENDEDOR`, `MECANICO` ou `GERENTE`.
- **Ciclo de vida:** Funcionários não são removidos fisicamente quando já possuem vínculos; usam soft delete.

### Clientes
Representa os proprietários de motocicletas ou compradores da loja.
- **Atributos:** Identificador (`id_cliente`), Nome (`nome_cliente`), CPF/CNPJ (`cpf_cnpj`), Telefone (`telefone`), Email (`email`), Endereço (`endereco`), Ativo (`ativo`).
- **Regras:** CPF ou CNPJ deve ser único no sistema.
- **Ciclo de vida:** A desativação é lógica e preserva o histórico operacional.

### Motos_Clientes
Representa os veículos pertencentes a clientes e utilizados no fluxo da oficina para manutenção, revisão e histórico de serviços.
- **Atributos:** Identificador (`id_moto_cliente`), Cliente Vinculado (`id_cliente`), Modelo (`modelo`), Placa (`placa`), Chassi (`chassi`), Ativo (`ativo`).
- **Relacionamento:** Pertence a um **Cliente**.
- **Regras:** Placa e Chassi devem ser únicos no sistema.
- **Ciclo de vida:** A desativação é lógica e não remove o veículo do histórico.

### Motos
Representa as motocicletas mantidas no estoque da loja e destinadas à venda. Esta entidade é independente de `motos_clientes` e não representa o veículo usado no histórico de oficina.
- **Atributos:** Identificador (`id`), Cliente opcional (`clientes_id`), Marca (`marca`), Modelo (`modelo`), Data de Cadastro (`created_at`).
- **Relacionamento:** Pode possuir um cliente associado quando a venda for registrada.

### Entrada_Mercadoria & Itens_Compra_Estoque
Representa a nota/registro de compra efetuada junto a um fornecedor para abastecimento de estoque.
- **Atributos Entrada:** Identificador (`id_entrada`), Fornecedor (`id_fornecedor`), Número do Documento (`numero_documento`), Funcionário Responsável (`id_funcionario`), Data da Entrada (`data_entrada`), Valor Total (`valor_total`).
- **Atributos Itens da Compra:** Identificador (`id_item_compra`), Entrada (`id_entrada`), Produto (`id_produto`), Quantidade (`quantidade`), Valor Unitário (`valor_unitario`, exibido como "preço de custo").
- **Relacionamentos:** Uma entrada possui um ou mais **Itens de Compra**, pertence a um **Fornecedor** e é registrada por um **Funcionário**.
- **Regras:** A quantidade deve ser estritamente positiva (`quantidade > 0`) e o valor unitário deve ser estritamente positivo (`valor_unitario > 0`).
- **Regras:** O fornecedor e todos os produtos devem existir e estar ativos; um mesmo produto não pode se repetir na entrada; `(id_fornecedor, numero_documento)` é único.
- **Regras financeiras:** `valor_total = Σ (quantidade × valor_unitario)`, calculado pelo Xano; valores enviados pelo cliente são ignorados.
- **Atomicidade:** cabeçalho, itens e incremento de `produtos.estoque_qtd` são gravados em uma única `db.transaction` por `POST entrada_mercadoria`. Qualquer rejeição desfaz a operação inteira.
- **Autoria:** `id_funcionario` e `data_entrada` são definidos pelo servidor a partir do usuário autenticado.
- **Ciclo de vida:** Entradas e itens são imutáveis após o registro; os endpoints de edição e exclusão respondem `403`. Estornos serão tratados em Change futura com movimentação inversa.
- **Concorrência:** o incremento lê e grava o saldo dentro da transação. Entradas simultâneas do mesmo produto podem, em teoria, sobrescrever uma à outra; o risco foi aceito dado o volume de operações.

### Ordens_Servico & Itens_Ordem_Servico
Representa o atendimento técnico prestado na oficina mecânica para a moto de um cliente.
- **Atributos OS:** Identificador (`id_os`), Moto do Cliente (`id_moto_cliente`), Funcionario Responsável (`id_funcionario`), Data de Abertura (`data_abertura`), Status (`status`).
- **Atributos Itens OS:** Identificador (`id_item_os`), Ordem de Serviço (`id_os`), Produto (`id_produto`), Quantidade (`quantidade`), Valor Total do Item (`valor_total_item`).
- **Relacionamentos:** Pertence a uma **Moto_Cliente**, é aberta por um **Funcionario** e é composta por vários **Produtos/Peças**.
- **Regras:** O status deve obrigatoriamente trafegar entre: `ABERTA`, `EM_ANDAMENTO`, `CONCLUIDA`, `CANCELADA`; `quantidade` e `valor_total_item` devem ser positivos.
- **Autoria:** `id_funcionario` deve ser derivado do funcionário vinculado ao usuário autenticado no Xano, nunca aceito como autoria arbitrária do cliente.

### Transacoes
Registra o fluxo financeiro de vendas e movimentações comerciais do estabelecimento.
- **Atributos:** Identificador (`id_transacao`), Tipo da Transação (`tipo_transacao`), Funcionário (`id_funcionario`), Cliente (`id_cliente`), Moto do Cliente (`id_moto_cliente`), Data (`data_transacao`), Valor Total (`valor_total`).
- **Regras:** O tipo de transação deve ser restrito aos valores: `MOTO`, `PECAS`, `BALCAO`, `COMPRA`, `ORDEM_SERVICO`.
- **Regras financeiras:** `valor_total` deve ser estritamente positivo (`> 0`).
- **Autoria:** `id_funcionario` deve ser derivado do usuário autenticado e do vínculo `user.id_funcionario`.

---

## Visão Consolidada (`vw_resumo_operacoes`)
O domínio conta com um consolidado conceitual de operações que unifica as **Transações Comerciais** e as **Entradas de Mercadorias** para relatórios e consultas gerais de fluxo operacional.