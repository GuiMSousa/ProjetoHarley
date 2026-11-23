# Delta de especificação: arquitetura e contratos

Alterações à spec `openspec/specs/arquitetura-e-contratos.md`, a aplicar no arquivamento.

## ADICIONADO — Requisito: redefinição de senha pelo gerente

Além da troca da própria senha (`reset/update_password`), o `GERENTE` PODE redefinir a senha de outro usuário `member` por `POST admin/usuarios/{id}/senha` (spec `administracao`). Esse caminho NÃO DEVE valer para o próprio gerente, para usuários com `role` `admin` nem para a conta de outro gerente. A senha NUNCA DEVE aparecer na resposta nem no `event_log`.

### Cenário: atalho para a própria senha

- **DADO** um `GERENTE` com um JWT válido, sem saber a senha atual
- **QUANDO** tentar redefinir a própria senha pelo painel
- **ENTÃO** a resposta DEVE ser `400`; a troca da própria senha continua exigindo a senha atual

## MODIFICADO — Requisito: exclusão somente lógica

Acrescentar ao requisito: "O `PATCH` de clientes, fornecedores, funcionários, motos de clientes e produtos DEVE aceitar qualquer subconjunto dos campos editáveis, declarados como entradas opcionais e explícitas, e DEVE gravar só os campos enviados. `{"ativo": false}` sozinho DEVE desativar o registro sem exigir os demais campos. O saldo de produto (`estoque_qtd`, `versao_estoque`) NÃO DEVE ser aceito pelo `PATCH`."

### Cenário: desativar pelo cadastro

- **DADO** um funcionário ativo
- **QUANDO** o gerente enviar `PATCH funcionarios/{id}` com `{"ativo": false}`
- **ENTÃO** a resposta DEVE ser `200`, com `ativo = false` e os demais campos inalterados (com `dblink`, a resposta era `400` "Missing param: nome_funcionario")

## MODIFICADO — Requisito: auditoria sem segredos

Acrescentar ao requisito: "A ação `admin_reset_password` DEVE registrar apenas `id_usuario`, `id_funcionario` e `id_gerente` em `metadata`."
