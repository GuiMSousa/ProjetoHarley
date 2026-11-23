# Nova spec: administração

Spec nova, `openspec/specs/administracao.md`, criada no arquivamento.

## Requisito: acesso ao painel

A rota `/admin` DEVE ser exclusiva do `GERENTE`, pela matriz `ROUTE_ROLES`. O `on_load` DEVE restaurar a sessão e só chamar o Xano quando `role_allows_route(role, "/admin")` for verdadeiro. Todo endpoint `admin/*` DEVE ter `enforce_role` com `GERENTE` como primeiro passo.

### Cenário: vendedor tenta abrir o painel

- **DADO** um `VENDEDOR` autenticado
- **QUANDO** abrir `/admin`
- **ENTÃO** DEVE ver a página de acesso negado, e nenhuma chamada `admin/*` DEVE ser feita

### Cenário: chamada direta à API

- **DADO** um JWT de `VENDEDOR` ou `MECANICO`
- **QUANDO** chamar `GET admin/usuarios`, `GET admin/eventos` ou `POST admin/usuarios/{id}/senha`
- **ENTÃO** a resposta DEVE ser `403` e nada DEVE ser lido ou gravado

## Requisito: lista de usuários sem segredos

`GET admin/usuarios` DEVE devolver, numa só consulta com `left join` em `funcionarios`, os campos `id`, `name`, `email`, `role`, `created_at`, `id_funcionario`, `nome_funcionario`, `tipo`, `cargo` e `ativo` de cada usuário. A resposta NÃO DEVE conter `password` nem `password_reset`. Um usuário sem funcionário vinculado DEVE aparecer com os campos do funcionário nulos, sem erro.

### Cenário: usuário criado pelo painel do Xano

- **DADO** um usuário sem `id_funcionario`
- **QUANDO** o gerente abrir a aba Usuários e acessos
- **ENTÃO** a lista DEVE responder `200` e mostrar o usuário como "sem funcionário vinculado"

## Requisito: criar acesso

O painel DEVE oferecer "Criar acesso" só para funcionários ativos sem usuário e DEVE usar `POST auth/signup` sem alterá-lo. A senha DEVE seguir a política da tabela `user` (mínimo de 8 caracteres, com ao menos uma letra e um número) e NÃO DEVE passar por `trim`. O formulário DEVE exigir a confirmação da senha.

### Cenário: funcionário já com acesso

- **DADO** um funcionário que já tem usuário
- **QUANDO** o gerente abrir "Criar acesso"
- **ENTÃO** esse funcionário NÃO DEVE aparecer na lista de opções

## Requisito: desativar e reativar acesso

"Desativar acesso" DEVE chamar `PATCH funcionarios/{id}` com `{"ativo": false}` depois de uma confirmação, e "Reativar acesso" DEVE chamá-lo com `{"ativo": true}`. O painel NÃO DEVE oferecer "Desativar acesso" na linha do próprio gerente.

### Cenário: acesso desativado

- **DADO** um vendedor com acesso
- **QUANDO** o gerente desativar o acesso dele
- **ENTÃO** a próxima chamada de negócio do vendedor DEVE responder `403`, e o próximo login DEVE ser recusado com "Seu funcionário está inativo."

## Requisito: redefinir a senha de outro usuário

`POST admin/usuarios/{id}/senha` DEVE receber `password` e `confirm_password`, com a política da tabela `user` e sem `trim`. O endpoint DEVE recusar, antes de gravar:

- o usuário inexistente, com `404`;
- o próprio gerente, com `400`, porque a troca da própria senha exige a senha atual;
- um usuário com `role` diferente de `member`, com `403`;
- a confirmação diferente da senha, com `400`.

A senha DEVE ser gravada só como hash. A resposta DEVE conter `id`, `name` e `email`, e NUNCA a senha. O endpoint DEVE registrar `log_event` com a ação `admin_reset_password` e `metadata` com `id_usuario`, `id_funcionario` e `id_gerente`.

### Cenário: gerente redefine a própria senha pelo painel

- **DADO** um `GERENTE` autenticado
- **QUANDO** enviar `POST admin/usuarios/{id}/senha` com o próprio `id`
- **ENTÃO** a resposta DEVE ser `400`, e a senha NÃO DEVE mudar

### Cenário: senha redefinida

- **DADO** um vendedor ativo
- **QUANDO** o gerente redefinir a senha dele
- **ENTÃO** o vendedor DEVE entrar com a senha nova
- **E** o `event_log` DEVE ter um registro `admin_reset_password` sem senha, hash ou token

## Requisito: auditoria de acessos

`GET admin/eventos` DEVE ler `event_log` paginado no servidor, com 25 registros por página, do mais recente para o mais antigo e com os totais da paginação. Cada registro DEVE trazer `id`, `created_at`, `action`, `user_id`, o nome do usuário e o do funcionário (por `left join`) e `metadata`. Os filtros opcionais são `action` e período (`inicio`/`fim`, de até 366 dias). Um período invertido ou maior que 366 dias DEVE responder `400`.

### Cenário: filtro por ação

- **DADO** eventos `login` e `signup` no período
- **QUANDO** o gerente filtrar por `signup`
- **ENTÃO** a lista DEVE trazer só os eventos `signup`, e os totais DEVEM contar só eles

## Requisito: parâmetros do sistema somente leitura

A aba Parâmetros do sistema DEVE mostrar, sem permitir edição:

- o prazo padrão e o máximo da reserva de moto;
- o limite de itens da venda de balcão;
- o limite de itens da entrada de mercadoria;
- o período máximo e o limite de operações do resumo financeiro.

Os valores DEVEM vir das constantes que o Reflex já aplica. Um contrato estático DEVE garantir que cada constante é igual ao valor aplicado no `.xs` correspondente.

### Cenário: regra alterada só no Xano

- **DADO** que alguém muda o máximo da reserva em `motos_id_reserva_POST.xs` de 30 para 15
- **QUANDO** a suíte offline rodar
- **ENTÃO** o contrato de parâmetros DEVE falhar até a constante do Reflex ser igualada
