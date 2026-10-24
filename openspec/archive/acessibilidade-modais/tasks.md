# Tarefas — Change 14: acessibilidade e UX dos modais

- [x] `modal_panel` com `rx.dialog` (Esc via `on_close`, clique fora bloqueado, `aria-modal`, descrição para leitores de tela e devolução do foco).
- [x] `modal_header` com `rx.dialog.title`.
- [x] `on_close` nos 14 modais (vitrine, vendas e reservas, balcão, oficina, cadastros e entradas); o financeiro não tem modal.
- [x] Overlay e `.sr-only` em `assets/harley.css`; ouvinte de foco no `head` do app.
- [x] `tests/test_modal_accessibility.py`: estrutura do diálogo, todo `modal_panel` com o mesmo `on_close` do cabeçalho e reset de cada modal pelo handler acionado no Esc.
- [x] Smoke no navegador (3 rodadas seguidas; inclui devolução do foco ao "Detalhes" e clique fora ignorado): foco inicial dentro do diálogo, `Tab` e `Shift+Tab` retidos, `aria-labelledby`/`aria-describedby` apontando para elementos com texto, e Esc fechando.
- [x] `ruff check .`, `compileall`, `reflex compile --dry` e `pytest tests/`.
- [x] Spec `design-system.md` (requisito de modais e cenário de teclado), `docs/quality.md` (cobertura do smoke) e `docs/setup.md` (débito resolvido).
- [x] Correções da revisão: o ouvinte de foco ignora focos com um modal aberto (opções do `rx.select` em portal), teste do ouvinte no `head`, smoke exige foco inicial no "Fechar" e cobre a opção removida, risco dos toasts corrigido na proposal.
- [ ] Mover para `openspec/archive/` e commit (usuário).
