# Tarefas — Change 13: carrossel e galeria multi-imagem

- [x] `get_lista_fotos_moto`, `indice_carrossel` e `get_foto_moto` no layout de pastas (`ui_helpers.py`).
- [x] `ModeloCatalogo.galeria: list[str]` (nula vira `[]`); `ModeloCard.fotos`.
- [x] `CatalogoState`: `foto_index`, `fotos_detalhe`, `foto_atual`, `proxima_foto`, `foto_anterior` e `selecionar_foto`; reset em `open_detail` e `select_cor`.
- [x] `VendasState`: `detalhe_fotos`, `foto_index`, `foto_atual` e os três handlers; reset ao abrir o detalhe.
- [x] `carrossel_fotos` nos modais da vitrine e de `/vendas` (coluna esquerda).
- [x] `tests/test_media.py` reescrito (layout de pastas, galeria, índice circular e carrossel nos dois estados).
- [x] `py_compile`, `reflex compile --dry` e `pytest tests/` (403 aprovados, 39 ignorados por opt-in).
- [x] Verificação no navegador (vitrine, 500 e 1440 px): seta, miniatura, borda laranja, `aria-current` e sem rolagem horizontal.
- [x] Spec `design-system.md`: delta pendente da Change 12 aplicado, mais o carrossel e o novo layout de fotos.
- [ ] Verificação autenticada do carrossel em `/vendas` (sem credenciais de teste no ambiente).
- [ ] Mover para `openspec/archive/` e commit (usuário).
