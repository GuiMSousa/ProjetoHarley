IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'DB_Concessionaria')
BEGIN
    CREATE DATABASE DB_Concessionaria;
END;

USE DB_Concessionaria;

-- ------------------------------------------------------------
-- 1. TABELA: Fornecedores
-- ------------------------------------------------------------
CREATE TABLE dbo.Fornecedores (
    id_fornecedor INT IDENTITY(1,1) NOT NULL,
    nome_fornecedor VARCHAR(100) NOT NULL,
    cnpj VARCHAR(18) NOT NULL,
    contato VARCHAR(50) NULL,
    CONSTRAINT PK_Fornecedores PRIMARY KEY CLUSTERED (id_fornecedor),
    CONSTRAINT UQ_Fornecedores_CNPJ UNIQUE (cnpj)
);
GO

-- ------------------------------------------------------------
-- 2. TABELA: Produtos
-- ------------------------------------------------------------
CREATE TABLE dbo.Produtos (
    id_produto INT IDENTITY(1,1) NOT NULL,
    nome_produto VARCHAR(100) NOT NULL,
    descricao VARCHAR(255) NULL,
    categoria VARCHAR(50) NOT NULL,
    estoque_qtd INT NOT NULL CONSTRAINT DF_Produtos_Estoque DEFAULT 0,
    preco_venda DECIMAL(10, 2) NOT NULL,
    CONSTRAINT PK_Produtos PRIMARY KEY CLUSTERED (id_produto),
    CONSTRAINT CK_Produtos_Estoque CHECK (estoque_qtd >= 0),
    CONSTRAINT CK_Produtos_Preco CHECK (preco_venda >= 0)
);
GO

-- ------------------------------------------------------------
-- 3. TABELA: Funcionarios
-- ------------------------------------------------------------
CREATE TABLE dbo.Funcionarios (
    id_funcionario INT IDENTITY(1,1) NOT NULL,
    nome_funcionario VARCHAR(100) NOT NULL,
    cargo VARCHAR(50) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    contato VARCHAR(50) NULL,
    CONSTRAINT PK_Funcionarios PRIMARY KEY CLUSTERED (id_funcionario),
    CONSTRAINT CK_Funcionarios_Tipo CHECK (tipo IN ('VENDEDOR', 'MECANICO', 'GERENTE'))
);
GO

-- ------------------------------------------------------------
-- 4. TABELA: Clientes
-- ------------------------------------------------------------
CREATE TABLE dbo.Clientes (
    id_cliente INT IDENTITY(1,1) NOT NULL,
    nome_cliente VARCHAR(100) NOT NULL,
    cpf_cnpj VARCHAR(18) NOT NULL,
    telefone VARCHAR(20) NULL,
    email VARCHAR(100) NULL,
    endereco VARCHAR(200) NULL,
    CONSTRAINT PK_Clientes PRIMARY KEY CLUSTERED (id_cliente),
    CONSTRAINT UQ_Clientes_CPF_CNPJ UNIQUE (cpf_cnpj)
);
GO

-- ------------------------------------------------------------
-- 5. TABELA: Motos_Clientes
-- ------------------------------------------------------------
CREATE TABLE dbo.Motos_Clientes (
    id_moto_cliente INT IDENTITY(1,1) NOT NULL,
    id_cliente INT NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    placa VARCHAR(10) NOT NULL,
    chassi VARCHAR(50) NOT NULL,
    CONSTRAINT PK_Motos_Clientes PRIMARY KEY CLUSTERED (id_moto_cliente),
    CONSTRAINT UQ_MotosClientes_Placa UNIQUE (placa),
    CONSTRAINT UQ_MotosClientes_Chassi UNIQUE (chassi),
    CONSTRAINT FK_MotosClientes_Cliente FOREIGN KEY (id_cliente)
        REFERENCES dbo.Clientes(id_cliente)
);
GO

-- ------------------------------------------------------------
-- 6. TABELA: Entrada_Mercadoria
-- ------------------------------------------------------------
CREATE TABLE dbo.Entrada_Mercadoria (
    id_entrada INT IDENTITY(1,1) NOT NULL,
    id_fornecedor INT NOT NULL,
    data_entrada DATETIME NOT NULL CONSTRAINT DF_Entrada_Data DEFAULT GETDATE(),
    valor_total DECIMAL(10, 2) NOT NULL CONSTRAINT DF_Entrada_Total DEFAULT 0.00,
    CONSTRAINT PK_Entrada_Mercadoria PRIMARY KEY CLUSTERED (id_entrada),
    CONSTRAINT FK_Entrada_Fornecedor FOREIGN KEY (id_fornecedor)
        REFERENCES dbo.Fornecedores(id_fornecedor)
);
GO

-- ------------------------------------------------------------
-- 7. TABELA: Itens_Compra_Estoque
-- ------------------------------------------------------------
CREATE TABLE dbo.Itens_Compra_Estoque (
    id_item_compra INT IDENTITY(1,1) NOT NULL,
    id_entrada INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    valor_unitario DECIMAL(10, 2) NOT NULL,
    CONSTRAINT PK_Itens_Compra_Estoque PRIMARY KEY CLUSTERED (id_item_compra),
    CONSTRAINT FK_ItensCompra_Entrada FOREIGN KEY (id_entrada)
        REFERENCES dbo.Entrada_Mercadoria(id_entrada),
    CONSTRAINT FK_ItensCompra_Produto FOREIGN KEY (id_produto)
        REFERENCES dbo.Produtos(id_produto),
    CONSTRAINT CK_ItensCompra_Qtd CHECK (quantidade > 0)
);
GO

-- ------------------------------------------------------------
-- 8. TABELA: Transacoes
-- ------------------------------------------------------------
CREATE TABLE dbo.Transacoes (
    id_transacao INT IDENTITY(1,1) NOT NULL,
    tipo_transacao VARCHAR(20) NOT NULL,
    id_funcionario INT NOT NULL,
    id_cliente INT NULL,
    id_moto_cliente INT NULL,
    data_transacao DATETIME NOT NULL CONSTRAINT DF_Transacao_Data DEFAULT GETDATE(),
    valor_total DECIMAL(10, 2) NOT NULL CONSTRAINT DF_Transacao_Total DEFAULT 0.00,
    CONSTRAINT PK_Transacoes PRIMARY KEY CLUSTERED (id_transacao),
    CONSTRAINT FK_Transacoes_Funcionario FOREIGN KEY (id_funcionario)
        REFERENCES dbo.Funcionarios(id_funcionario),
    CONSTRAINT FK_Transacoes_Cliente FOREIGN KEY (id_cliente)
        REFERENCES dbo.Clientes(id_cliente),
    CONSTRAINT FK_Transacoes_MotoCliente FOREIGN KEY (id_moto_cliente)
        REFERENCES dbo.Motos_Clientes(id_moto_cliente),
    CONSTRAINT CK_Transacoes_Tipo CHECK (tipo_transacao IN ('MOTO', 'PECAS', 'BALCAO', 'COMPRA', 'ORDEM_SERVICO'))
);
GO

-- ------------------------------------------------------------
-- 9. TABELA: Ordens_Servico
-- ------------------------------------------------------------
CREATE TABLE dbo.Ordens_Servico (
    id_os INT IDENTITY(1,1) NOT NULL,
    id_moto_cliente INT NOT NULL,
    id_funcionario INT NOT NULL,
    data_abertura DATETIME NOT NULL CONSTRAINT DF_OS_Data DEFAULT GETDATE(),
    status VARCHAR(20) NOT NULL CONSTRAINT DF_OS_Status DEFAULT 'ABERTA',
    CONSTRAINT PK_Ordens_Servico PRIMARY KEY CLUSTERED (id_os),
    CONSTRAINT FK_OS_MotoCliente FOREIGN KEY (id_moto_cliente)
        REFERENCES dbo.Motos_Clientes(id_moto_cliente),
    CONSTRAINT FK_OS_Funcionario FOREIGN KEY (id_funcionario)
        REFERENCES dbo.Funcionarios(id_funcionario),
    CONSTRAINT CK_OS_Status CHECK (status IN ('ABERTA', 'EM_ANDAMENTO', 'CONCLUIDA', 'CANCELADA'))
);
GO

-- ------------------------------------------------------------
-- 10. TABELA: Itens_Ordem_Servico
-- ------------------------------------------------------------
CREATE TABLE dbo.Itens_Ordem_Servico (
    id_item_os INT IDENTITY(1,1) NOT NULL,
    id_os INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    valor_total_item DECIMAL(10, 2) NOT NULL,
    CONSTRAINT PK_Itens_Ordem_Servico PRIMARY KEY CLUSTERED (id_item_os),
    CONSTRAINT FK_ItensOS_OrdensServico FOREIGN KEY (id_os)
        REFERENCES dbo.Ordens_Servico(id_os),
    CONSTRAINT FK_ItensOS_Produtos FOREIGN KEY (id_produto)
        REFERENCES dbo.Produtos(id_produto),
    CONSTRAINT CK_ItensOS_Qtd CHECK (quantidade > 0)
);
GO