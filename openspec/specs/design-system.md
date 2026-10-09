# Especificação: design system Harley-Davidson

## Requisito: tokens centralizados

Toda cor usada pela aplicação DEVE estar em `Projeto_HarleyStore/styles/theme.py` ou em `assets/harley.css`; nenhum outro módulo DEVE conter literais `#RRGGBB` ou `rgba(`. A paleta base DEVE ser preto asfalto `#000000`, preto fosco `#121212`, cinza industrial `#1A1A1A`, laranja Harley `#FF6600`, branco `#FFFFFF` e cinza metálico `#A0A0A0`.

## Requisito: contraste

Todo par de texto e fundo declarado nos tokens (`TEXT_PAIRS`, incluindo as cores de status) DEVE atingir 4,5:1 (WCAG AA). Texto sobre o laranja DEVE ser preto; texto branco sobre `#FF6600` (2,94:1) NÃO DEVE ser usado.

## Requisito: tipografia e identidade

Títulos (`rx.heading`) DEVEM aparecer em caixa alta com a fonte Oswald e o corpo em Inter, ambas de licença livre; a caixa alta DEVE ser aplicada por CSS, preservando o texto original. A aplicação NÃO DEVE usar fontes proprietárias da marca. A identidade DEVE ser o logo fornecido pela loja (`assets/HARLEY_LOGO.png`, escudo recortado de `assets/harley-davidson-logo.webp` com fundo transparente, exibido com 45 px de altura) seguido do título "HARLEY STORE", no canto superior esquerdo de todas as rotas: topo da sidebar (alinhado aos ícones do menu), barra superior no celular, cabeçalho da vitrine pública e login. Onde o espaço é estreito (sidebar, menu móvel, vitrine no celular), o subtítulo "Concessionária e oficina" DEVE ser ocultado. O acento do Radix (foco, abas, seleção) DEVE ser `#FF6600`.

## Requisito: componentes compartilhados

Páginas DEVEM usar os componentes de `ui_helpers.py` (`page_header`, `card`, `primary_button`, `metal_button`, `danger_button`, `data_table`, `toolbar`, `pager`, `empty_state`, `stat_tile`, `swatch`, `status_badge`, `labeled`, `error_callout`) e o shell de `components.py` (`app_shell`, `public_shell`, `modal_panel`, `page_body`). Um único `status_badge` DEVE cobrir os status de OS, de motos e de cadastros.

### Cenário: badge de status

- **DADO** uma OS `EM_ANDAMENTO` e uma moto `RESERVADA`
- **QUANDO** forem exibidas em qualquer tela
- **ENTÃO** ambas DEVEM usar o mesmo componente, com as cores fixas do mapa `STATUS_COLORS`

## Requisito: responsividade

Abaixo de 768 px a navegação interna DEVE ficar num menu lateral recolhível; a vitrine DEVE caber em 390 px sem rolagem horizontal da página, com as abas de família roláveis. Todas as páginas DEVEM caber em 500 px sem rolagem horizontal da página; tabelas largas rolam dentro do próprio card.

## Requisito: estados de carregamento

Todo botão que envia um formulário ou confirma um modal DEVE trocar o rótulo por um texto de progresso terminado em "…" (ex.: "Salvando…", "Registrando venda…") e ficar desabilitado enquanto o pedido ao Xano estiver em curso; listas DEVEM mostrar "Carregando…" durante a carga. Como o Reflex só envia o estado ao navegador ao terminar o handler ou num `yield`, o handler DEVE fazer `yield` logo depois de ligar a flag e antes de chamar o Xano.

### Cenário: duplo clique em "Confirmar venda"

- **DADO** o modal de venda preenchido
- **QUANDO** o vendedor clicar duas vezes seguidas em "Confirmar venda"
- **ENTÃO** o botão DEVE mostrar "Registrando venda…" desabilitado após o primeiro clique e apenas uma venda DEVE ser enviada

## Requisito: acessibilidade

- Campos de formulário DEVEM ter rótulo associado (`labeled` renderiza `<label>`); campos sem rótulo visível (busca, login) DEVEM ter `aria-label`, e o login DEVE declarar `autocomplete` (`username`, `current-password`).
- O shell DEVE oferecer um link "Pular para o conteúdo", primeiro item do Tab, que leva o foco ao `<main id="conteudo">`.
- Modais DEVEM declarar `role="dialog"` e `aria-modal`; erros DEVEM ser anunciados (`role="alert"`); ícones decorativos DEVEM ter `aria-hidden`.
- A folha global DEVE declarar `color-scheme: dark`, respeitar `prefers-reduced-motion`, usar algarismos tabulares nas tabelas e a página DEVE declarar `theme-color` igual ao fundo.
- O logo DEVE ter no máximo 45 px de altura, caixa reservada (`width`/`height`) e texto alternativo "Harley-Davidson", que substitui a imagem se o arquivo faltar.
