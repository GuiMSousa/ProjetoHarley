# Modelo do Domínio - HarleyStore

## Entidades e Conceitos Principais

### Cliente
Representa o utilizador registrado que navega e realiza compras na loja.
- **Atributos Principais:** Nome, email, telefone, endereço de entrega.
- **Relacionamentos:** Um Cliente pode realizar múltiplos Pedidos.

### Produto
Representa os itens e acessórios disponíveis para venda no catálogo.
- **Atributos Principais:** Nome, descrição, preço, quantidade em stock, categoria.
- **Relacionamentos:** Um Produto pode ser associado a múltiplos Itens de Pedido.

### Pedido
Representa uma transação de compra efetuada por um Cliente.
- **Atributos Principais:** Data, estado (Pendente, Pago, Enviado, Cancelado), valor total.
- **Relacionamentos:** Pertence a um único Cliente e contém vários Produtos.