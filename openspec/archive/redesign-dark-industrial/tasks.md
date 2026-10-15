# Tarefas — Change 12: redesign Dark Industrial Premium

## 1. Mídia

- [x] `get_foto_moto(moto, imagem_url=None)` em `ui_helpers.py` (`MOTOS_DIR`, placeholders, slug sem acentos).
- [x] `ModeloCatalogo.imagem_principal` opcional e `galeria: list[str] = []`.
- [x] Vitrine (`modelo_card` e fotos por cor) e `/vendas` (`moto_row["foto"]`) usando `get_foto_moto`.

## 2. Estética

- [x] `styles/theme.py`: fundo `#0D0D0D`, superfície `#161616`, borda `#262626`, `SHADOWS["glow"]`, `CARD_HOVER` e brilho no hover do botão primário.
- [x] Selos foscos com borda (`status_badge`) e paleta `STATUS_COLORS` com AA.
- [x] `assets/harley.css`: fundo e painel do Radix espelhando o tema.

## 3. Visão geral

- [x] `dashboard_state.py`: `KPI_ROLES`, `kpis_visiveis`, `montar_kpis` e `DashboardState.load_dashboard` (com `yield`).
- [x] `dashboard_pages.py`: cartões de indicadores e atalhos de ação redesenhados; `on_load` da rota `/`.

## 4. Vitrine e `/vendas`

- [x] Cartão da vitrine com foto 16:9 e selo fosco flutuante.
- [x] Modal da vitrine em 2 colunas, sem chassi (D2).
- [x] Detalhe da unidade em `/vendas` em 2 colunas, com Reservar/Vender.
- [x] `open_reserva` e `open_venda` com carregamento e `yield` antes do Xano.

## 5. Testes e verificação

- [x] `tests/test_media.py` e `tests/test_dashboard_state.py` (novos).
- [x] `tests/test_theme.py` (paleta nova, brilho e selos) e `tests/test_loading_states.py` (`load_dashboard`, `open_reserva`, `open_venda`).
- [x] `py_compile`, `reflex compile --dry` e `pytest tests/` (395 aprovados, 39 ignorados por opt-in).
- [x] Verificação visual da vitrine e do modal a 500 e 1440 px, com o app em produção.
- [ ] Verificação visual autenticada (visão geral e `/vendas`): sem credenciais de teste no ambiente.

## 6. Arquivamento

- [x] Aplicar o delta de `specs/design-system.md` em `openspec/specs/` (aplicado em 2026-10-15, com a Change 13).
- [ ] Atualizar `docs/project-structure.md` (`dashboard_state.py`, `assets/motos/`).
- [ ] Mover para `openspec/archive/` e commit (usuário).
