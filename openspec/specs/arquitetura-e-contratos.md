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

Desde a Change 8, `POST motos` (somente `GERENTE`) DEVE aceitar apenas `id_modelo`, `chassi`, `cor`, `ano_modelo` e `preco_venda`; status, cliente, vendedor e validade NUNCA vêm do payload. As regras completas estão na spec `catalogo-vendas-motos` (requisito "cadastro de unidades").

### Cenário: payload de moto com status

- **DADO** um payload de unidade com `status = VENDIDA` e `clientes_id`
- **QUANDO** o endpoint `POST motos` for executado
- **ENTÃO** a unidade DEVE nascer `DISPONIVEL`, sem cliente, e esses campos DEVEM ser ignorados

## Requisito: vínculo de identidade

A tabela `user` DEVE possuir o campo opcional `id_funcionario` como referência a `funcionarios.id`.

### Cenário: usuário vinculado

- **DADO** um usuário com `id_funcionario` preenchido
- **ENTÃO** o valor DEVE identificar um registro existente em `funcionarios`
- **E** o campo `user.role` DEVE continuar sendo tratado como papel técnico separado do tipo do funcionário

## Requisito: grupos de API do Xano

O cliente DEVE endereçar cada grupo de APIs pela sua própria URL base: `XANO_API_BASE_URL` para o grupo `HARLEY` e `XANO_AUTH_API_BASE_URL` para o grupo `Authentication`.

### Cenário: login em grupo distinto

- **DADO** grupos `Authentication` e `HARLEY` com canonicals diferentes
- **QUANDO** o usuário fizer login e depois listar clientes
- **ENTÃO** `auth/login` e `auth/me` DEVEM usar a URL do grupo `Authentication`
- **E** `clientes` DEVE usar a URL do grupo `HARLEY`

## Requisito: funcionário ativo

Somente usuários vinculados a um funcionário com `ativo != false` PODEM executar operações de negócio.

### Cenário: funcionário desativado

- **DADO** um usuário cujo funcionário foi desativado
- **QUANDO** chamar qualquer endpoint de negócio
- **ENTÃO** o Xano DEVE responder `403`
- **E** o Reflex NÃO DEVE considerar a sessão autenticada

## Requisito: superfície pública mínima

Somente `auth/login` e a vitrine de leitura `GET catalogo` e `GET catalogo/{id}` (Change 8) PODEM ser chamados sem JWT. A vitrine DEVE expor apenas campos de vitrine de modelos ativos, nunca unidades, chassi, cliente, vendedor ou histórico. Qualquer outro endpoint público DEVE ser aprovado por Change e incluído na lista explícita do teste de superfície pública. Recursos auxiliares do quick-start sem uso pela aplicação (como o agente e a ferramenta de exemplo de IA) NÃO DEVEM ser mantidos no export. `auth/signup` e `message/send_welcome_email` DEVEM exigir `GERENTE`; `auth/signup` NÃO DEVE devolver token do usuário criado. Fluxos de recuperação de acesso não homologados DEVEM permanecer bloqueados.

### Cenário: gerente cria usuário

- **DADO** um gerente autenticado
- **QUANDO** criar um usuário para um funcionário ativo sem usuário
- **ENTÃO** a resposta DEVE conter o id do usuário criado e nenhum token

## Requisito: troca de senha autenticada

`reset/update_password` DEVE exigir `current_password`, `password` (mínimo de 8 caracteres) e `confirm_password`, validar o funcionário vinculado ativo e conferir a senha atual antes de gravar. A nova senha DEVE diferir da atual, e as senhas NÃO DEVEM passar por `trim`.

### Cenário: token sem a senha atual

- **DADO** um JWT válido de um usuário
- **QUANDO** alguém tentar trocar a senha informando uma senha atual incorreta ou omitindo-a
- **ENTÃO** a resposta DEVE ser `400` e a senha NÃO DEVE mudar

## Requisito: exclusão somente lógica

O `DELETE` de clientes, motos de clientes, produtos, fornecedores, funcionários e motos da loja DEVE responder `403`; a desativação é feita por `PATCH` com `ativo = false`. O `DELETE` de transações também DEVE responder `403`, sem desativação: transações são imutáveis (spec `financeiro`). A única exclusão física permitida é a de item de OS `ABERTA` ou `EM_ANDAMENTO`, que devolve a peça ao estoque.

### Cenário: exclusão forjada

- **DADO** um gerente autenticado
- **QUANDO** enviar `DELETE produtos/{id}`
- **ENTÃO** a resposta DEVE ser `403` e o produto, seus itens de OS e suas movimentações DEVEM permanecer intactos

## Requisito: helpers compartilhados da interface

Componentes e regras repetidos entre páginas DEVEM viver em módulos compartilhados: `ui_helpers.py` (`labeled`, `error_callout`, `operation_is_blocked`) e `feedback.py` (`error_feedback`, `toast_error`, `toast_success`). Os estados NÃO DEVEM chamar `rx.toast` diretamente nem importar funções de outros estados de página.

## Requisito: leitura tolerante e observável

Os DTOs de leitura DEVEM ser separados dos de escrita (Change 15).

- Campos de exibição (textos, imagens, cores e preço de vitrine) DEVEM aceitar nulo ou formato fora do padrão, com valor padrão. Uma URL de imagem que não seja `http(s)` ou caminho local NÃO DEVE ser aceita.
- Identidade, vínculo e regras de negócio (ids, chaves, enums, saldo ≥ 0, preço de peça > 0) DEVEM continuar estritos.
- As listas do cliente Xano DEVEM ser validadas registro a registro. O registro inválido DEVE ser descartado e registrado em log com endpoint, índice, `id` e os campos e tipos do erro, NUNCA com os valores.
- Uma lista sem nenhum registro válido, ou uma resposta que não seja lista, DEVE continuar sendo erro.
- Telas que combinam fontes DEVEM isolar a falha de cada uma: os KPIs da visão geral, e as unidades e os modelos em `/vendas`.
- As mensagens DEVEM distinguir falha de conexão, dados fora do contrato e erro interno do Xano.

### Cenário: registro criado fora do app

- **DADO** uma unidade com status fora do enum, gravada direto no painel do Xano
- **QUANDO** `/vendas` carregar
- **ENTÃO** as demais unidades DEVEM aparecer, sem mensagem de erro, e o log DEVE registrar o descarte sem os valores do registro

### Cenário: uma fonte da visão geral falha

- **DADO** um vendedor na visão geral
- **QUANDO** a lista de motos responder `500`
- **ENTÃO** o KPI de OS DEVE aparecer, o de motos DEVE mostrar "—" e a mensagem DEVE indicar erro interno do Xano

## Requisito: autoria imutável

Nenhum endpoint DEVE gravar `id_funcionario` vindo do payload. Transações não têm correção manual; o autor é sempre o funcionário do JWT da operação que as criou.

## Requisito: papel verificado em todo endpoint autenticado

Todo endpoint com `auth = "user"` DEVE chamar `Quick Start/enforce_role`, que exige funcionário vinculado, existente e ativo e o papel mínimo da operação. A única exceção é `auth/me`, que devolve apenas a identidade de quem chama, para o Reflex explicar um funcionário inativo. IDs de funcionário recebidos no payload (`id_mecanico` na abertura de OS, `id_funcionario` no `auth/signup`) DEVEM ser validados no servidor (existente, ativo e do tipo esperado).

### Cenário: token válido de funcionário desativado

- **DADO** um JWT válido de um usuário cujo funcionário foi desativado
- **QUANDO** chamar qualquer endpoint de negócio, inclusive `logs/user/my_events`
- **ENTÃO** a resposta DEVE ser `403`

## Requisito: dados financeiros restritos

`GET transacoes` e `GET transacoes/{id}` DEVEM exigir `GERENTE`. Lançamentos, correções e exclusões manuais (`POST transacoes`, `PUT`/`PATCH`/`DELETE transacoes/{id}`) DEVEM responder `403` para qualquer perfil: transações nascem somente das operações de negócio (venda de moto, conclusão de OS e lançamento retroativo) e são imutáveis (spec `financeiro`).

### Cenário: vendedor tenta lançar uma transação

- **DADO** um `VENDEDOR` autenticado
- **QUANDO** enviar `POST transacoes` com um `valor_total`
- **ENTÃO** a resposta DEVE ser `403` e nada DEVE ser gravado

### Cenário: gerente tenta corrigir uma transação

- **DADO** um `GERENTE` autenticado
- **QUANDO** enviar `PATCH transacoes/{id}` com outro `valor_total`
- **ENTÃO** a resposta DEVE ser `403` "Transações são imutáveis." e a transação NÃO DEVE mudar

## Requisito: itens de transação imutáveis

`itens_transacao` (Change 11) DEVE ser gravada somente por `POST balcao/vendas`, na mesma transação da transação `BALCAO`; NÃO DEVEM existir rotas genéricas de leitura ou escrita para a tabela. O preço do item DEVE ser a fotografia de `produtos.preco_venda` lida pelo Xano, nunca do payload. A rota `/balcao` e o `POST balcao/vendas` DEVEM aceitar somente `GERENTE` e `VENDEDOR` (spec `vendas-balcao`).

### Cenário: mecânico tenta vender no balcão

- **DADO** um `MECANICO` autenticado
- **QUANDO** enviar `POST balcao/vendas`
- **ENTÃO** a resposta DEVE ser `403` e nada DEVE ser gravado
- **E** `/balcao` NÃO DEVE aparecer na navegação dele

## Requisito: auditoria sem segredos

Registros de `event_log` NÃO DEVEM conter senha, hash ou token; `metadata` DEVE ser composto por campos explícitos, nunca pelo registro `user` completo.
