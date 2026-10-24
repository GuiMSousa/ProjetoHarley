# Tarefas — Change 15: resiliência de leitura, DTOs tolerantes e observabilidade

- [x] `xano_client.py`: `_list` validando registro a registro, log sem valores, `XanoResponseError` para lista inválida por inteiro, logs de resposta de objeto inválida e de 5xx, `XanoConnectionError`.
- [x] Texto de leitura tolerante compartilhado (`services/leitura.py`).
- [x] `catalogo.py`: `VariacaoCor` de leitura tolerante e segura, `VariacaoCorCreate` estrita, `ModeloMoto` e `ModeloCatalogo` tolerantes.
- [x] `cadastros.py`: classes de leitura próprias para `Cliente`, `MotoCliente`, `Produto`, `Fornecedor` e `Funcionario`; `ativo` nulo vale verdadeiro.
- [x] `ordens_servico.py`: `Mecanico` com nome tolerante.
- [x] Telas: "Preço sob consulta" na vitrine; formulário de modelo com preço nulo.
- [x] `dashboard_state.py`: um `try` por fonte de KPI.
- [x] `vendas_state.py`: falha nos modelos preserva as unidades.
- [x] `feedback.py`: mensagens de rede, de contrato de dados e de 5xx.
- [x] Testes de regressão com JSON malformado (cliente, DTOs, telas e mensagens); testes antigos atualizados para a separação leitura/escrita. Mutações: as 8 não equivalentes derrubam a suíte nova.
- [x] `ruff check .`, `compileall`, `reflex compile --dry` e `pytest tests/` (429 aprovados, 42 ignorados por opt-in); smoke de navegador com o catálogo real (3 aprovados).
- [x] Spec `arquitetura-e-contratos.md` (requisito de leitura tolerante e observável), `docs/xano-api-client.md` (erros e logs) e `docs/quality.md`.
- [x] Reprodução de ponta a ponta (2026-10-22): app real com um Xano simulado devolvendo a vitrine pública mais um modelo "cadastrado pelo painel" (hex sem `#`, foto relativa, sem imagem nem preço). Antes desta change, a vitrine inteira sumia com "Não foi possível comunicar com o Xano"; agora os 5 modelos aparecem. Achado corrigido: a amostra de uma cor sem hex legível aparecia com o laranja de destaque do botão; agora é um anel vazio (`swatch`), com teste.
- [ ] Mover para `openspec/archive/` e commit (usuário).
