# Especificação: design system Harley-Davidson

## Requisito: tokens centralizados

Toda cor usada pela aplicação DEVE estar em `Projeto_HarleyStore/styles/theme.py` ou em `assets/harley.css`; nenhum outro módulo DEVE conter literais `#RRGGBB` ou `rgba(`. A paleta base (Change 12, Dark Industrial Premium) DEVE ser obsidiana `#0D0D0D` (fundo), preto fosco `#121212` (barras e molduras), cinza industrial `#161616` com borda `#262626` (cartões e painéis), laranja Harley `#FF6600`, branco `#FFFFFF` e cinza metálico `#A0A0A0`.

## Requisito: contraste

Todo par de texto e fundo declarado nos tokens (`TEXT_PAIRS`, incluindo as cores de status) DEVE atingir 4,5:1 (WCAG AA). Texto sobre o laranja DEVE ser preto; texto branco sobre `#FF6600` (2,94:1) NÃO DEVE ser usado.

## Requisito: tipografia e identidade

Títulos (`rx.heading`) DEVEM aparecer em caixa alta com a fonte Oswald e o corpo em Inter, ambas de licença livre; a caixa alta DEVE ser aplicada por CSS, preservando o texto original. A aplicação NÃO DEVE usar fontes proprietárias da marca. A identidade DEVE ser o logo fornecido pela loja (`assets/HARLEY_LOGO.png`, escudo recortado de `assets/harley-davidson-logo.webp` com fundo transparente, exibido com 45 px de altura) seguido do título "HARLEY STORE", no canto superior esquerdo de todas as rotas: topo da sidebar (alinhado aos ícones do menu), barra superior no celular, cabeçalho da vitrine pública e login. Onde o espaço é estreito (sidebar, menu móvel, vitrine no celular), o subtítulo "Concessionária e oficina" DEVE ser ocultado. O acento do Radix (foco, abas, seleção) DEVE ser `#FF6600`.

## Requisito: componentes compartilhados

Páginas DEVEM usar os componentes de `ui_helpers.py` (`page_header`, `card`, `primary_button`, `metal_button`, `danger_button`, `data_table`, `toolbar`, `pager`, `empty_state`, `stat_tile`, `swatch`, `status_badge`, `labeled`, `error_callout`) e o shell de `components.py` (`app_shell`, `public_shell`, `modal_panel`, `page_body`). Um único `status_badge` DEVE cobrir os status de OS, de motos e de cadastros. O selo DEVE ser fosco: fundo escuro, texto e borda finos na cor do status (motos: `DISPONIVEL` esmeralda `#34D399`, `RESERVADA` âmbar `#FBBF24`, `VENDIDA` grafite `#A3A3A3`); status desconhecidos (ex.: "Sob consulta" na vitrine) usam o grafite do fallback.

### Cenário: badge de status

- **DADO** uma OS `EM_ANDAMENTO` e uma moto `RESERVADA`
- **QUANDO** forem exibidas em qualquer tela
- **ENTÃO** ambas DEVEM usar o mesmo componente, com as cores fixas do mapa `STATUS_COLORS`

## Requisito: brilho no hover

O botão primário e os cartões interativos (atalhos da visão geral e cartões da vitrine) DEVEM ganhar, no hover, a borda laranja e a sombra `0 0 15px rgba(255, 102, 0, 0.25)` (`SHADOWS["glow"]`, `CARD_HOVER`).

## Requisito: fotos das motos

Toda foto de moto DEVE vir do Xano (Change 17): `imagem_principal` (URL https), a `galeria` do modelo (imagens públicas enviadas pelo painel) e as fotos das cores. O projeto NÃO DEVE ter fotos locais por modelo. Em `ui_helpers.py`:

- `get_foto_moto(moto, imagem_url=None)` DEVE devolver a foto da cor; senão a `imagem_principal`; senão `FOTO_INDISPONIVEL`. Uma foto só é usada se for `http(s)` e não for placeholder (`placehold.co` e afins).
- `get_lista_fotos_moto(moto, imagem_url=None)` DEVE devolver a `galeria` do Xano, só com URLs reais; senão a foto única de `get_foto_moto`. Uma foto de cor real ausente da galeria DEVE abrir a lista.
- `FOTO_INDISPONIVEL` DEVE ser uma imagem neutra embutida (SVG em `data:`, nas cores do tema), sem arquivo e sem requisição.

### Cenário: modelo sem foto no Xano

- **DADO** um modelo com `imagem_principal` em `placehold.co` e sem `galeria`
- **QUANDO** a vitrine for exibida
- **ENTÃO** o cartão e o carrossel DEVEM mostrar `FOTO_INDISPONIVEL`, sem nenhuma requisição que responda 404

## Requisito: visão geral executiva

A rota `/` DEVE mostrar cartões de indicadores filtrados pelo perfil, carregados com `yield` antes do Xano: Faturamento do mês e Vendas de balcão só para `GERENTE`; Motos em estoque (disponíveis e reservadas) para `GERENTE` e `VENDEDOR`; OS ativas (abertas e em andamento) para todos. Abaixo, os atalhos das áreas que o perfil pode abrir.

## Requisito: detalhes em duas colunas com carrossel

O modal de detalhe da vitrine e o de detalhe da unidade em `/vendas` DEVEM ter duas colunas a partir de 768 px (abaixo disso, empilhadas): à esquerda, o carrossel de fotos em moldura escura com sombra; à direita, a ficha e as ações. O modal da vitrine NÃO DEVE mostrar chassi. O carrossel (`carrossel_fotos`, Change 13) DEVE:

- mostrar a foto de `foto_index`, que volta a 0 ao abrir um detalhe e ao escolher uma cor (a foto da cor passa a ser a primeira);
- ter setas `chevron-left` e `chevron-right` sobre a foto, com `aria-label`, quando houver mais de uma foto; a navegação DEVE dar a volta nas pontas;
- ter miniaturas clicáveis abaixo, a ativa com borda `2px solid #FF6600`, opacidade 100% e `aria-current="true"`.

### Cenário: navegar pelas fotos

- **DADO** o detalhe de um modelo com quatro fotos, na primeira
- **QUANDO** o visitante clicar na seta da esquerda
- **ENTÃO** DEVE ver a quarta foto, com a quarta miniatura destacada

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
- Erros DEVEM ser anunciados (`role="alert"`); ícones decorativos DEVEM ter `aria-hidden`.
- Todo modal DEVE usar o `modal_panel` (Change 14), um `rx.dialog` com `role="dialog"`, `aria-modal="true"`, `aria-labelledby` no título do `modal_header` e `aria-describedby` numa descrição para leitores de tela. Ao abrir, o foco DEVE ir para o primeiro controle (o botão "Fechar"); o `Tab` DEVE ficar preso no diálogo; o Esc DEVE executar o mesmo handler do "Fechar"; um clique fora NÃO DEVE fechar; ao fechar, o foco DEVE voltar ao controle que o abriu.
- A folha global DEVE declarar `color-scheme: dark`, respeitar `prefers-reduced-motion`, usar algarismos tabulares nas tabelas e a página DEVE declarar `theme-color` igual ao fundo.
- O logo DEVE ter no máximo 45 px de altura, caixa reservada (`width`/`height`) e texto alternativo "Harley-Davidson", que substitui a imagem se o arquivo faltar.

### Cenário: fechar um modal pelo teclado

- **DADO** o detalhe de um modelo aberto na vitrine pelo botão "Detalhes"
- **QUANDO** o usuário navega com `Tab` e `Shift+Tab` e depois pressiona Esc
- **ENTÃO** o foco DEVE permanecer dentro do diálogo enquanto ele estiver aberto, o diálogo DEVE fechar com o Esc e o foco DEVE voltar ao botão "Detalhes"
