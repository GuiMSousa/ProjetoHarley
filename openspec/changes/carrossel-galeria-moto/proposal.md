# Proposta: carrossel e galeria multi-imagem no detalhe da moto (Change 13)

## Contexto e objetivo

Change pedida diretamente para execução (2026-10-15). As fotos locais passaram a ficar numa pasta por modelo (`assets/motos/<slug>/1..4.<slug>.jpg` e `default_<slug>.png`). O objetivo é mostrar a galeria inteira nos modais de detalhe da vitrine e de `/vendas`, num carrossel com setas e miniaturas, sem mudar regras de negócio nem o Xano.

## Escopo

- **Mídia (`ui_helpers.py`):**
  - `get_lista_fotos_moto(moto, imagem_url=None)`: a `galeria` do Xano (só URLs reais), senão as fotos locais existentes em ordem, senão a foto única;
  - `get_foto_moto` passa a ler a nova estrutura de pastas;
  - `indice_carrossel` faz a navegação dar a volta nas pontas.
- **DTO:** `ModeloCatalogo.galeria: list[str]` (nula vira `[]`), já mapeada para quando o Xano a enviar.
- **Estado:** `foto_index`, `proxima_foto()`, `foto_anterior()` e `selecionar_foto(index)` em `CatalogoState` e `VendasState`. O índice volta a 0 ao abrir um detalhe e ao escolher uma cor (a foto da cor abre o carrossel).
- **UI:** `carrossel_fotos` compartilhado, com a foto principal, setas `chevron-left`/`chevron-right` sobrepostas quando há mais de uma foto e miniaturas clicáveis. A miniatura ativa tem borda `2px solid #FF6600`, opacidade 100% e `aria-current`.

## Decisões

- **D1 — Galeria só no Reflex:** o Xano ainda não tem o campo `galeria` (a vitrine pública só devolve os campos aprovados). O DTO já o aceita. Incluí-lo na tabela e no `Catalogo/vitrine` é uma mudança de banco e de contrato público, para outra Change.
- **D2 — Só arquivos existentes:** a galeria local lista apenas as fotos que existem (não as quatro às cegas), para não exibir miniaturas quebradas.
- **D3 — Foto da cor primeiro:** escolher uma cor coloca a foto dela no início do carrossel (dedupe com a galeria) e volta o índice a 0. É o comportamento que o modal já tinha antes do carrossel.

## Fora do escopo

- Campo `galeria` no Xano e upload de fotos.
- Swipe por gesto e autoplay.

## Status

Apply concluído em 2026-10-15 (ver `tasks.md`). Spec `design-system.md` atualizada diretamente (com o delta pendente da Change 12).
