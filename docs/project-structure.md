# Estrutura do Projeto

Esta página explica onde cada tipo de arquivo deve ficar. A ideia é permitir que uma nova funcionalidade seja acompanhada do início ao fim sem procurar arquivos em várias áreas.

## Fluxo de trabalho

1. Entenda o problema em `docs/project-overview.md`.
2. Confira entidades e regras em `docs/domain-model.md`.
3. Crie uma mudança pequena em `openspec/changes/` antes de implementar uma alteração significativa.
4. Escreva ou altere o código da aplicação em `Projeto_HarleyStore/`.
5. Coloque imagens e arquivos estáticos em `assets/`.
6. Valide com `python -m pytest` (ou `python -m unittest discover -s tests`), `python -m py_compile`, `reflex compile --dry` e o validador XanoScript; publique o backend com `xano workspace push -d ./xano` (ver `docs/xano-api-client.md`).
7. Atualize a documentação e os artefatos da mudança quando o comportamento estiver concluído.

## Pastas principais

| Pasta | Responsabilidade |
| --- | --- |
| `Projeto_HarleyStore/` | Ponto de entrada e componentes da aplicação Reflex. |
| `assets/` | Recursos estáticos usados pela aplicação, incluindo `harley.css` (sobrescritas globais do tema) e o logo `HARLEY_LOGO.png` (escudo recortado de `harley-davidson-logo.webp`, com fundo transparente, usado no cabeçalho). |
| `Projeto_HarleyStore/styles/theme.py` | Tokens do design system (cores, tipografia, status, contraste); única origem de cores junto com `assets/harley.css`. |
| `Projeto_HarleyStore/financeiro_state.py`, `financeiro_pages.py` e `services/financeiro.py` | Visão consolidada `/financeiro` (Change 10): período, cartões de receitas, despesas e saldo, totais por tipo e operações; somente `GERENTE`. |
| `Projeto_HarleyStore/balcao_state.py`, `balcao_pages.py` e `services/balcao.py` | Venda no balcão `/balcao` (Change 11): busca de peças, carrinho, cliente opcional, confirmação e recibo; `GERENTE` e `VENDEDOR`. Os helpers de busca de produtos (`produto_row`, `filtrar_produtos`) ficam em `listing.py`, compartilhados com a oficina. |
| `Projeto_HarleyStore/ui_helpers.py` e `components.py` | Componentes compartilhados (cabeçalho, tabela, botões, badges, swatches) e shell (sidebar, vitrine pública, modal). |
| `docs/` | Visão geral, domínio e decisões que ajudam no entendimento do sistema. |
| `tests/` | Suíte pytest/unittest: contratos XanoScript, DTOs, cliente e estados. `conftest.py` aplica os marcadores `integration`, `writes` e `concurrency`; `event_runner.py` executa handlers geradores como o Reflex. A configuração fica em `pytest.ini` e as dependências de teste em `requirements-dev.txt`. |
| `xano/` | Exports, tabelas e endpoints do backend oficial Xano. Não são importados diretamente pelo Reflex. |
| `openspec/` | Propostas, especificações, designs e tarefas de mudanças incrementais. |
| `.vscode/` | Configurações e integrações específicas do editor. |

## Pastas geradas

`.venv/`, `.states/`, `.web/`, `__pycache__/` e `reflex.lock/` são criadas por ferramentas. Não coloque código manual nelas.

## Regra simples

Código da aplicação fica em `Projeto_HarleyStore/`; documentação fica em `docs/`; contratos e exports do Xano ficam em `xano/`; especificação de mudança fica em `openspec/`.