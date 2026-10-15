# Delta de especificação: design system Harley-Davidson

Alterações à spec `openspec/specs/design-system.md`, a aplicar no arquivamento da Change 12.

## MODIFICADO — Requisito: tokens centralizados

A frase da paleta base DEVE ser substituída por: "A paleta base DEVE ser obsidiana `#0D0D0D` (fundo da aplicação), preto fosco `#121212` (barras e molduras), cinza industrial `#161616` com borda `#262626` (cartões e painéis), laranja Harley `#FF6600`, branco `#FFFFFF` e cinza metálico `#A0A0A0`."

## ADICIONADO — Requisito: brilho no hover

O botão primário e os cartões interativos (atalhos da visão geral e cartões da vitrine) DEVEM ganhar, no hover, a borda laranja e a sombra `0 0 15px rgba(255, 102, 0, 0.25)` (`SHADOWS["glow"]`, `CARD_HOVER`).

## MODIFICADO — Requisito: componentes compartilhados

Acrescentar: o `status_badge` DEVE ser fosco, com fundo escuro e texto e borda finos na cor do status. Motos: `DISPONIVEL` esmeralda (`#34D399`), `RESERVADA` âmbar (`#FBBF24`), `VENDIDA` grafite (`#A3A3A3`). Status desconhecidos (ex.: "Sob consulta" na vitrine) DEVEM usar o grafite do fallback. Cada texto DEVE manter 4,5:1 sobre o próprio fundo.

## ADICIONADO — Requisito: fotos das motos

`get_foto_moto(moto, imagem_url=None)` (`ui_helpers.py`) DEVE resolver a foto nesta ordem: a imagem do Xano (ou a da cor), se não for vazia nem placeholder; a foto local `/motos/<slug>.jpg`; a arte padrão `/motos/default_<slug com _>.png`. Um modelo sem nenhuma arte local DEVE manter o placeholder remoto, em vez de uma imagem quebrada. Vitrine e `/vendas` DEVEM usar essa função.

### Cenário: placeholder no Xano

- **DADO** o modelo "Fat Boy" com `imagem_principal` em `placehold.co`
- **QUANDO** a vitrine for exibida
- **ENTÃO** o cartão DEVE mostrar `/motos/fat-boy.jpg`

## ADICIONADO — Requisito: visão geral executiva

A rota `/` DEVE mostrar cartões de indicadores filtrados pelo perfil, carregados com `yield` antes do Xano: Faturamento do mês e Vendas de balcão só para `GERENTE`; Motos em estoque (disponíveis e reservadas) para `GERENTE` e `VENDEDOR`; OS ativas (abertas e em andamento) para todos. Abaixo, os atalhos das áreas que o perfil pode abrir.

### Cenário: vendedor na visão geral

- **DADO** um `VENDEDOR` autenticado
- **QUANDO** abrir `/`
- **ENTÃO** DEVE ver Motos em estoque e OS ativas, e NÃO DEVE ver nem carregar Faturamento e Vendas de balcão

## ADICIONADO — Requisito: detalhes em duas colunas

O modal de detalhe da vitrine e o de detalhe da unidade em `/vendas` DEVEM ter duas colunas a partir de 768 px: à esquerda, a foto em moldura escura com sombra; à direita, a ficha e as ações. Abaixo disso, as colunas DEVEM empilhar. O modal da vitrine NÃO DEVE mostrar chassi.
