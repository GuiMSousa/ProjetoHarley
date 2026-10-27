# Tarefas — Change 17: fotos das motos vindas do Xano

- [x] `xano/table/modelos_moto.xs` com `galeria` e `default_motos` como publicadas; `Catalogo/vitrine` com `galeria` (paths); `Vendas/detalhe_moto` com `galeria`; `GET motos` com `imagem_principal`. Validador do MCP.
- [x] DTOs: `galeria` como URLs absolutas (`path` do Xano + origem de `XANO_API_BASE_URL`); `MotoEstoque` com `imagem_principal` e `galeria`; foto de cor só http(s).
- [x] `get_foto_moto` e `get_lista_fotos_moto` sem arquivos locais, com a imagem neutra embutida.
- [x] Remover `assets/motos/` e `.web/public/motos/`.
- [x] Testes com URLs remotas (`test_media.py` reescrito, `test_catalogo.py`, `test_resiliencia_leitura.py`; `test_ui_helpers.py` não tinha caminho local), contratos dos `.xs` e smoke exigindo foto remota ou a imagem neutra.
- [x] Specs (`design-system.md`, `catalogo-vendas-motos.md`, `arquitetura-e-contratos.md`) e docs.
- [x] `ruff`, `compileall`, `reflex compile --dry`, `pytest` (437 aprovados, 42 ignorados), smoke de navegador (2 aprovados; o carrossel é ignorado até o push, porque cada modelo tem uma foto) e `--dry-run` direcionado (só `Catalogo/vitrine`, `Vendas/detalhe_moto` e `GET motos`). Na vitrine local, as 6 fotos vêm do Xano e nenhuma resposta dá erro.
- [x] Push e fotos da galeria pelo painel (usuário): a vitrine publicada devolve 4 fotos por modelo, públicas (20/20 com 200).
- [x] Revisão (2026-10-27): `galeria` só com arquivos não privados (`$$.access != "private"`) na vitrine e no detalhe; `url_de_midia` com esquema sem diferença de maiúsculas, `http` promovido a `https` e recusa de `..` (inclusive `%2e%2e` e barra invertida); foto principal e de cor pelo mesmo saneador. Testes com mutação (5 variantes pegas).
- [ ] Push de `Catalogo/vitrine` e `Vendas/detalhe_moto` com o filtro de privados (OK do usuário).
- [x] Mover para o archive e commit (usuário): commit `8937ea8`.
