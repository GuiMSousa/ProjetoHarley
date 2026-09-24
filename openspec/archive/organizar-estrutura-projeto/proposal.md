# Proposta: regularizar arquitetura, contratos e alinhamento do OpenSpec

## Problema

A documentação e os artefatos versionados ainda possuem referências a uma estrutura que não corresponde ao projeto atual. A aplicação Reflex utiliza o pacote `Projeto_HarleyStore`, enquanto documentos da Change citam um nome de pacote legado e uma movimentação de `xano/` que não foi realizada.

Além disso, o domínio não diferencia explicitamente as motocicletas de clientes das motocicletas mantidas em estoque para venda. Os contratos também não expressam de forma uniforme que preços e valores unitários devem ser estritamente maiores que zero. Existem ainda dois desalinhamentos técnicos: o endpoint de criação de `motos` ignora o payload recebido e a identidade `user` não possui o vínculo documentado com `Funcionarios`.

## Objetivo

Alinhar a arquitetura documentada, o modelo de domínio, os contratos OpenSpec e os exports Xano com a estrutura real do projeto, preparando uma base coerente para as próximas Changes funcionais.

## Escopo

- Atualizar esta Change e suas referências para utilizar `Projeto_HarleyStore` como pacote oficial do Reflex.
- Manter `xano/` como a localização versionada dos exports Xano, salvo decisão arquitetural posterior aprovada.
- Definir `motos_clientes` como a entidade de veículos pertencentes a clientes e utilizados no fluxo da oficina.
- Definir `motos` como a entidade de motocicletas em estoque da loja destinadas à venda.
- Atualizar o modelo e os contratos para exigir `preco_venda`, `valor_unitario` e demais valores de preço aplicáveis estritamente maiores que zero (`> 0`), preservando `estoque_qtd >= 0` e quantidades positivas.
- Corrigir `xano/api/harley/motos_POST.xs` para persistir todos os campos válidos recebidos no payload, além de `created_at`.
- Adicionar `id_funcionario` como referência de `user` para `funcionarios`, conforme o modelo de identidade e autorização documentado.
- Atualizar design, tasks e especificações da Change para descrever decisões, critérios de aceite e validações correspondentes.

## Fora do escopo

- Criar telas ou fluxos funcionais no frontend Reflex.
- Implementar login, logout, renovação de sessão ou autorização por cargo.
- Implementar movimentação automática de estoque, vendas, entradas de mercadoria ou ordens de serviço.
- Criar a visão consolidada `vw_resumo_operacoes`.
- Mover `xano/` para outra pasta de integração.
- Alterar endpoints que não sejam necessários para os alinhamentos descritos nesta Change.

## Critérios de aceite

- Todos os artefatos da Change usam `Projeto_HarleyStore` como nome do pacote da aplicação.
- A documentação distingue sem ambiguidade `motos_clientes` e `motos`.
- Os contratos da Change rejeitam preços e valores unitários iguais a zero ou negativos.
- O POST de `motos` persiste os campos de domínio recebidos e não somente `created_at`.
- `user.id_funcionario` referencia `funcionarios.id` e fica disponível para o modelo de autorização posterior.
- A compilação/validação dos exports e dos arquivos Python afetados é executada antes do Archive.