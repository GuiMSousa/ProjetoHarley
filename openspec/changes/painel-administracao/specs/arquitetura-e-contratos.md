# Delta de especificação: arquitetura e contratos

Alterações à spec `openspec/specs/arquitetura-e-contratos.md`, a aplicar no arquivamento.

## ADICIONADO — Requisito: redefinição de senha pelo gerente

Além da troca da própria senha (`reset/update_password`), o `GERENTE` PODE redefinir a senha de outro usuário `member` por `POST admin/usuarios/{id}/senha` (spec `administracao`). Esse caminho NÃO DEVE valer para o próprio gerente nem para usuários com `role` `admin`. A senha NUNCA DEVE aparecer na resposta nem no `event_log`.

### Cenário: atalho para a própria senha

- **DADO** um `GERENTE` com um JWT válido, sem saber a senha atual
- **QUANDO** tentar redefinir a própria senha pelo painel
- **ENTÃO** a resposta DEVE ser `400`; a troca da própria senha continua exigindo a senha atual

## MODIFICADO — Requisito: auditoria sem segredos

Acrescentar ao requisito: "A ação `admin_reset_password` DEVE registrar apenas `id_usuario`, `id_funcionario` e `id_gerente` em `metadata`."
