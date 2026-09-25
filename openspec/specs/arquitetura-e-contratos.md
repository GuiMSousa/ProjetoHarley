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

O endpoint `POST motos` DEVE persistir todos os campos de domínio recebidos no payload (`clientes_id`, `marca` e `modelo`) e o timestamp de criação.

### Cenário: payload de moto

- **DADO** um payload válido para uma motocicleta de estoque
- **QUANDO** o endpoint `POST motos` for executado
- **ENTÃO** os campos recebidos DEVEM aparecer no registro criado

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

Somente `auth/login` PODE ser chamado sem JWT. Recursos auxiliares do quick-start sem uso pela aplicação (como o agente e a ferramenta de exemplo de IA) NÃO DEVEM ser mantidos no export. `auth/signup` e `message/send_welcome_email` DEVEM exigir `GERENTE`; `auth/signup` NÃO DEVE devolver token do usuário criado. Fluxos de recuperação de acesso não homologados DEVEM permanecer bloqueados.

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

O `DELETE` de clientes, motos de clientes, produtos, fornecedores, funcionários, motos da loja e transações DEVE responder `403`; a desativação é feita por `PATCH` com `ativo = false`. A única exclusão física permitida é a de item de OS `ABERTA` ou `EM_ANDAMENTO`, que devolve a peça ao estoque.

### Cenário: exclusão forjada

- **DADO** um gerente autenticado
- **QUANDO** enviar `DELETE produtos/{id}`
- **ENTÃO** a resposta DEVE ser `403` e o produto, seus itens de OS e suas movimentações DEVEM permanecer intactos

## Requisito: helpers compartilhados da interface

Componentes e regras repetidos entre páginas DEVEM viver em módulos compartilhados: `ui_helpers.py` (`labeled`, `error_callout`, `operation_is_blocked`) e `feedback.py` (`error_feedback`, `toast_error`, `toast_success`). Os estados NÃO DEVEM chamar `rx.toast` diretamente nem importar funções de outros estados de página.

## Requisito: autoria imutável

Nenhum endpoint DEVE gravar `id_funcionario` vindo do payload. Em `PATCH` de OS e transações, a chave DEVE ser descartada antes da gravação.

## Requisito: auditoria sem segredos

Registros de `event_log` NÃO DEVEM conter senha, hash ou token; `metadata` DEVE ser composto por campos explícitos, nunca pelo registro `user` completo.
