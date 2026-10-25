# Design: regularização de arquitetura e contratos

## Decisões

- `Projeto_HarleyStore/` é o pacote oficial da aplicação Reflex e permanece no mesmo nível de `rxconfig.py`.
- `xano/` permanece na raiz como fonte versionada dos schemas, endpoints e funções do backend oficial.
- `motos_clientes` representa veículos pertencentes a clientes e usados pela oficina.
- `motos` representa motocicletas mantidas em estoque para venda.
- `produtos.preco_venda` e `itens_compra_estoque.valor_unitario` devem ser estritamente maiores que zero. Quantidades de itens continuam estritamente positivas e `produtos.estoque_qtd` pode ser zero, mas nunca negativo.
- `user.id_funcionario` é uma referência opcional a `funcionarios.id`. A autorização por cargo permanece fora desta Change.

## Contratos Xano

O endpoint de criação de `motos` deve persistir `clientes_id`, `marca` e `modelo` recebidos no payload, além do timestamp de criação. O campo `clientes_id` continua opcional para permitir o cadastro de estoque antes da venda.

Os limites positivos são aplicados no schema Xano, para que a API rejeite valores inválidos independentemente do cliente que a consuma.

## Consequências

- A documentação deixa de sugerir uma pasta de integração que não existe.
- Os nomes das entidades de motocicletas deixam explícita a separação entre estoque e oficina.
- A Change estabelece o vínculo estrutural de identidade sem antecipar a implementação de login ou permissões.