# Proposta: acessibilidade e UX dos modais (Change 14)

## Contexto e objetivo

Change pedida diretamente para execução (2026-10-15). Fecha o débito "modais sem Esc nem foco preso", registrado no audit e em `docs/setup.md`. Hoje o `modal_panel` é uma `rx.box` com `role="dialog"` e `aria-modal`:
- não fecha com Esc;
- não leva o foco para dentro ao abrir;
- deixa o `Tab` escapar para a página de trás;
- não declara título nem descrição para leitores de tela.

O objetivo é corrigir isso em todos os modais, sem mudar regras de negócio nem o Xano.

## Escopo

- **`modal_panel` (`components.py`):**
  - passa a usar o `rx.dialog` do Reflex (Radix Dialog), que traz focus trap, foco inicial no primeiro elemento interativo (o botão "Fechar" do cabeçalho) e o vínculo automático de `aria-labelledby`/`aria-describedby`; a devolução do foco ao fechar é feita à parte (D5);
  - recebe `on_close`, que o Esc aciona;
  - mantém `role="dialog"` e declara `aria-modal="true"`.
- **`modal_header` (`ui_helpers.py`):** o título vira `rx.dialog.title`, que dá nome ao diálogo (`aria-labelledby`).
- **Descrição:** cada modal ganha uma `rx.dialog.description` visível só para leitores de tela ("Pressione Esc para fechar."), que alimenta o `aria-describedby`.
- **Aplicação:** os 14 modais que usam `modal_panel` passam o próprio handler de fechamento: vitrine, vendas e reservas, balcão, oficina, cadastros e entradas. O financeiro não tem modal.
- **Estilo:** o overlay mantém o escurecimento e o desfoque atuais (CSS em `assets/harley.css`), e o painel mantém largura e rolagem interna. A borda laranja do topo já não aparecia antes desta change, porque o `border` do `CARD` sobrescreve o `border_top`; isso fica fora do escopo.

## Decisões

- **D1 — Radix Dialog em vez de handler de teclado próprio:** `on_key_down` ou um listener de janela resolveria o Esc, mas o focus trap exigiria JavaScript próprio. O `rx.dialog` é o mecanismo do Reflex para isso e cobre Esc, foco e ARIA de uma vez, num único componente compartilhado.
- **D2 — Esc chama o mesmo handler do "Fechar":** o comportamento de fechar (inclusive o reset de cada formulário) continua num só lugar por modal.
- **D3 — Clique fora não fecha:** o padrão do Radix fecharia o modal ao clicar no overlay. Isso descartaria formulários longos (OS, venda) por acidente, então o clique fora é bloqueado. Fecham o modal apenas o Esc e o botão "Fechar", como hoje.
- **D4 — Foco inicial no "Fechar":** é o primeiro elemento interativo de todos os modais, o que atende ao requisito ("primeiro campo ou botão de fechar") sem configuração por modal.
- **D5 — Devolução do foco por script curto:** o Radix só devolve o foco a um `Dialog.Trigger`, e estes modais abrem pelo state. Sem ajuste, o foco cairia no `body` ao fechar, uma regressão em relação ao modal antigo, que nunca tirava o foco do botão. Um ouvinte `focusin` no `head` (`rx.script`) guarda o último controle focado enquanto nenhum modal está aberto, e o `on_close_auto_focus` (`rx.call_script`) volta a focá-lo, se ainda estiver na página. A regra é "nenhum modal aberto", e não "fora do diálogo", porque as opções do `rx.select` ficam num portal fora do diálogo e sairiam da página antes do fechamento.

## Fora do escopo

- Mudanças de layout ou de conteúdo dos modais.
- Confirmação antes de descartar um formulário preenchido.

## Riscos

- O conteúdo do diálogo passa a ser renderizado num portal no fim do `body`. Enquanto o modal está aberto, o Radix marca o resto da página como `aria-hidden`, exceto as regiões `aria-live`: a biblioteca `aria-hidden` que ele usa as preserva, então os toasts continuam anunciados pelos leitores de tela (conferido no navegador). Os erros de formulário também são anunciados dentro do modal (`error_callout` com `role="alert"`).

## Status

Apply concluído em 2026-10-15 (ver `tasks.md`). Spec `design-system.md` atualizada diretamente (requisito de acessibilidade e cenário de teclado).
