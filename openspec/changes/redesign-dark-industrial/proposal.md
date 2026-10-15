# Proposta: redesign UI/UX e mídia visual — Dark Industrial Premium (Change 12)

## Contexto e objetivo

Change pedida diretamente para execução (2026-10-14), sem fase Propose separada; esta pasta registra o escopo, as decisões e o que foi feito. O objetivo é dar à aplicação o visual "Dark Industrial Premium" da marca e fotos reais das motos, sem mudar regras de negócio, endpoints nem permissões.

## Escopo

- **Mídia:** `get_foto_moto(moto, imagem_url=None)` em `ui_helpers.py` resolve a foto:
  1. a imagem do Xano, se não for vazia nem placeholder (`placehold.co` e similares);
  2. a foto local `/motos/<slug>.jpg` (ex.: `fat-boy.jpg`);
  3. a arte padrão `/motos/default_<slug>.png` (ex.: `default_fat_boy.png`).

  Usada nos cartões e no modal da vitrine, nas fotos por cor e nas unidades de `/vendas`. O DTO `ModeloCatalogo` passa a aceitar `imagem_principal` nula e ganha `galeria: list[str] = []`, ainda sem uso.
- **Estética:**
  - fundo `#0D0D0D`, cartões e painéis `#161616` com borda `#262626`;
  - brilho laranja no hover (`0 0 15px rgba(255, 102, 0, 0.25)`) no botão primário e nos cartões interativos;
  - selos de status foscos (fundo escuro, texto e borda na cor do status): Disponível esmeralda, Reservada âmbar, Vendida grafite. Os demais status seguem o mesmo padrão.
- **Visão geral (`/`):**
  - cartões de indicadores (Faturamento do mês, Motos em estoque, OS ativas, Vendas de balcão);
  - atalhos de ação com ícone laranja em destaque e contorno com brilho no hover.
- **Vitrine:** cartão com foto 16:9 e selo flutuante; modal de detalhe em 2 colunas (foto emoldurada | ficha e ações).
- **`/vendas`:**
  - detalhe da unidade em 2 colunas (foto | modelo, cor, chassi, preço e ações Reservar/Vender);
  - abrir Reservar ou Vender passa a mostrar carregamento (`yield` antes do Xano).

## Decisões tomadas pelas specs vigentes

- **D1 — Indicadores por perfil:** dados financeiros são só do `GERENTE` (spec `financeiro`). Faturamento e Vendas de balcão aparecem só para ele; Motos em estoque para `GERENTE` e `VENDEDOR`; OS ativas para todos. Cada perfil só chama no Xano o que já pode ler.
- **D2 — Vitrine sem chassi:** a vitrine pública NÃO DEVE expor chassi nem unidades (spec `catalogo-vendas-motos`). Por isso o modal da vitrine mostra a ficha do modelo, e chassi e as ações Reservar/Vender ficam no modal de detalhe da unidade em `/vendas` (autenticado).
- **D3 — Um único `status_badge`:** os selos foscos continuam num só componente (spec `design-system`); o selo "Sob consulta" da vitrine usa o cinza grafite do fallback.

## Fora do escopo

- Galeria de fotos (o campo `galeria` fica preparado, sem tela).
- Endpoints, tabelas e permissões do Xano (nenhuma mudança).
- Fechar modais com Esc e prender o foco (débito anterior).

## Status

Apply concluído em 2026-10-14 (ver `tasks.md`). Deltas de spec em `specs/`, a aplicar no arquivamento.
