# Proposta: resiliência de leitura, DTOs tolerantes e observabilidade (Change 15)

## Contexto e objetivo

Change pedida diretamente para execução (2026-10-22), a partir do diagnóstico da mesma data. Um registro inserido direto no Xano, sem passar pelos endpoints que validam as regras, tirou do ar ao mesmo tempo a vitrine, a visão geral e `/vendas`. O processo do Reflex não caiu: a cascata veio de quatro causas.

1. Os DTOs de **leitura** herdavam as regras de **escrita** (`class Cliente(CadastroModel, ClienteCreate)`, `VariacaoCor` com regex de `hex` e de URL). O app recusava ler dados que o banco aceitou.
2. Cada lista era validada inteira (`TypeAdapter(list[...])`): um registro inválido derrubava a lista toda.
3. As telas tratavam erros "tudo ou nada": a visão geral apagava todos os KPIs, e `/vendas` apagava as unidades quando só os modelos falhavam.
4. A mensagem "Não foi possível comunicar com o Xano" aparecia também para erros de dados, e nada era registrado em log.

O objetivo é que um registro fora do contrato afete só a si mesmo: ele é exibido com valores padrão ou descartado com log, as telas isolam a falha de cada fonte, as mensagens distinguem rede de dados e o log permite o diagnóstico sem expor dados.

## Escopo

- **Cliente Xano (`services/xano_client.py`):**
  - as listas passam a ser validadas registro a registro (`_list`);
  - um registro inválido gera um log `WARNING` com endpoint, índice, `id` e os campos e tipos de erro, nunca os valores, e é descartado;
  - uma resposta que não é lista, ou em que todos os registros são inválidos, continua sendo `XanoResponseError`;
  - respostas de objeto inválidas e respostas 5xx também passam a ser registradas em log;
  - timeout e falha de conexão ganham o tipo `XanoConnectionError` (subclasse de `XanoError`).
- **DTOs de leitura separados dos de escrita:**
  - `VariacaoCor` (leitura) tolerante, normalizando `hex` inválido e URL que não seja `http(s)` ou caminho local para vazio; `VariacaoCorCreate` (escrita) mantém as regras atuais;
  - `ModeloMoto` e `ModeloCatalogo`: nome e imagem nulos viram vazio; preço base e "a partir de" nulos viram `None` ("Preço sob consulta");
  - `Cliente`, `MotoCliente`, `Produto`, `Fornecedor` e `Funcionario`: classes de leitura próprias, que não herdam mais de `*Create`. Textos nulos viram vazio, sem `min_length` nem regex de código, a placa vazia é aceita e `ativo` nulo vale verdadeiro;
  - `Mecanico`: nome nulo vira vazio.
- **Visão geral (`dashboard_state.py`):** cada fonte (OS, motos, faturamento) tem seu próprio `try`. Uma fonte com falha deixa só o seu KPI em "—", e a sessão expirada continua levando ao login.
- **`/vendas` (`vendas_state.py`):** os modelos do gerente são carregados à parte. Uma falha neles mostra a mensagem, mas preserva as unidades.
- **Mensagens (`feedback.py`):** falha de rede, erro de contrato de dados e resposta 5xx passam a ter avisos diferentes.

## Decisões

- **D1 — Descartar o registro inválido, com log, em vez de falhar a lista:** um registro fora do contrato afeta só a si mesmo.
- **D2 — Uma lista sem nenhum registro válido continua sendo erro:** se nada passa, quem mudou foi o contrato; mostrar uma lista vazia esconderia o problema.
- **D3 — Tolerância só nos campos de exibição:** textos, imagens, cores e preço de vitrine. Identidade, vínculo e regra de negócio continuam estritos na leitura: `id`, chaves, enums de status, família e tipo, saldo ≥ 0 e preço de venda de peça > 0. Quem os viola é descartado (D1).
- **D4 — Log sem dados:** os erros do pydantic são registrados com `include_input=False`, e o registro é identificado só por endpoint, índice e `id` numérico. Parâmetros de busca não entram no log.
- **D5 — Escrita inalterada:** `*Create` e `*Update` mantêm todas as regras, inclusive `https://` e `#RRGGBB` nas cores (`catalogo-vendas-motos.md`).
- **D6 — Registro descartado aparece só no log:** foi o pedido. Um aviso na tela fica para outra change.
- **D7 — URL de leitura segura:** ao tirar o regex da leitura, uma `imagem_url` que não seja `http(s)` ou caminho local (`javascript:` ou `data:`, por exemplo) vira vazio. A tela cai na foto local.

## Fora do escopo

- Aviso de "N registros ignorados" na interface.
- Cache da vitrine servindo o último catálogo bom quando o Xano falha.
- Mudanças no Xano: validar `variacoes_cor` nos endpoints de leitura e combinar o procedimento de inserção pelo painel.
- Financeiro: `ResumoFinanceiro` continua estrito, porque os totais não podem omitir operações em silêncio.

## Riscos

- Um registro descartado some da lista sem aviso visual; só o log o mostra. Por exemplo, uma unidade com status fora do enum não aparece em `/vendas`.
- Registros com texto vazio aparecem com campos em branco (por exemplo, um cliente sem CPF).

## Status

Apply concluído em 2026-10-22 (ver `tasks.md`). Spec `arquitetura-e-contratos.md` atualizada diretamente (requisito de leitura tolerante e observável).
