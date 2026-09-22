# Estrutura do Projeto

Esta página explica onde cada tipo de arquivo deve ficar. A ideia é permitir que uma nova funcionalidade seja acompanhada do início ao fim sem procurar arquivos em várias áreas.

## Fluxo de trabalho

1. Entenda o problema em `docs/project-overview.md`.
2. Confira entidades e regras em `docs/domain-model.md`.
3. Crie uma mudança pequena em `openspec/changes/` antes de implementar uma alteração significativa.
4. Escreva ou altere o código da aplicação em `LOJAHARLEY/`.
5. Coloque imagens e arquivos estáticos em `assets/`.
6. Valide a aplicação com `python -m py_compile` e `reflex run`.
7. Atualize a documentação e os artefatos da mudança quando o comportamento estiver concluído.

## Pastas principais

| Pasta | Responsabilidade |
| --- | --- |
| `LOJAHARLEY/` | Ponto de entrada e componentes da aplicação Reflex. |
| `assets/` | Recursos estáticos usados pela aplicação. |
| `docs/` | Visão geral, domínio e decisões que ajudam no entendimento do sistema. |
| `integrations/xano/` | Exports do Xano. São referência de integração e não são importados diretamente pelo Reflex. |
| `openspec/` | Propostas, especificações, designs e tarefas de mudanças incrementais. |
| `.vscode/` | Configurações e integrações específicas do editor. |

## Pastas geradas

`.venv/`, `.states/`, `.web/`, `__pycache__/` e `reflex.lock/` são criadas por ferramentas. Não coloque código manual nelas.

## Regra simples

Código da aplicação fica em `LOJAHARLEY/`; documentação fica em `docs/`; integração externa fica em `integrations/`; especificação de mudança fica em `openspec/`.