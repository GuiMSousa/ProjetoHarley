# Qualidade

## Comandos

Rode na raiz com o `.venv`. A verificação da base é lint, sintaxe, testes e build, nessa ordem; os demais checks são opt-in. O runtime mínimo é Python >= 3.12 (genéricos PEP 695), que é também o alvo do ruff (`target-version = "py312"`), para que nenhuma correção automática traga sintaxe mais nova. Desenvolvimento e execução usam 3.14.

Os comandos opt-in recebem variáveis de ambiente. No Git Bash, a variável vem antes do comando e vale só para ele (`HARLEY_BROWSER_URL=http://localhost:3100 .venv/Scripts/python -m pytest -m browser`). No PowerShell, a variável persiste no processo até o `Remove-Item Env:VAR`, e a forma depende do efeito:

- **Variáveis que não alteram estado** (`HARLEY_BROWSER_URL`, `XANO_TEST_LIVE`) usam linha única:

  ```powershell
  $env:HARLEY_BROWSER_URL='http://localhost:3100'; .venv/Scripts/python -m pytest -m browser; Remove-Item Env:HARLEY_BROWSER_URL
  ```

- **Variáveis que gravam no Xano** (`XANO_TEST_ALLOW_WRITES`, `XANO_TEST_CONCURRENCY`) usam sempre `try`/`finally`. Na linha única, o `Remove-Item` é pulado se a execução for interrompida (erro ou Ctrl+C), e o próximo `pytest` comum gravaria no Xano de produção:

  ```powershell
  try { $env:XANO_TEST_ALLOW_WRITES='true'; .venv/Scripts/python -m pytest -m integration } finally { Remove-Item Env:XANO_TEST_ALLOW_WRITES }
  ```

  Com as corridas, remova as duas:

  ```powershell
  try { $env:XANO_TEST_ALLOW_WRITES='true'; $env:XANO_TEST_CONCURRENCY='true'; .venv/Scripts/python -m pytest -m integration } finally { Remove-Item Env:XANO_TEST_ALLOW_WRITES, Env:XANO_TEST_CONCURRENCY -ErrorAction SilentlyContinue }
  ```

| Check | Comando | O que prova | O que não prova |
| --- | --- | --- | --- |
| Lint | `.venv/Scripts/ruff check .` | Regras padrão do ruff 0.17 com alvo Python 3.12: imports e variáveis sem uso, nomes indefinidos, padrões frágeis | Comportamento |
| Sintaxe | `.venv/Scripts/python -m compileall -q Projeto_HarleyStore tests rxconfig.py` | Todos os módulos compilam no runtime | Imports e lógica |
| Testes | `.venv/Scripts/python -m pytest` | DTOs, cliente HTTP com respostas simuladas, States e handlers (via `tests/event_runner.py`) e contratos estáticos dos `.xs` (RBAC, transações, validações) | O Xano real: o cliente é simulado |
| Build | `.venv/Scripts/reflex compile --dry` | A árvore de componentes do Reflex compila | Que o servidor sobe ou a tela funciona |
| Navegador (opt-in) | Com o app rodando (`reflex run --env prod --single-port --backend-port 3100`): `HARLEY_BROWSER_URL=http://localhost:3100 .venv/Scripts/python -m pytest -m browser` (PowerShell: `$env:HARLEY_BROWSER_URL='http://localhost:3100'; .venv/Scripts/python -m pytest -m browser; Remove-Item Env:HARLEY_BROWSER_URL`) | No Edge instalado: `/catalogo` abre um modelo e o carrossel avança e volta; o diálogo prende o foco (`Tab`/`Shift+Tab`), tem `aria-labelledby`/`aria-describedby` com texto, ignora clique fora, fecha com Esc e devolve o foco ao "Detalhes"; uma rota protegida sem sessão mostra o login; nenhum erro no console | Fluxos autenticados (não há credenciais de teste) |
| Integração (opt-in) | `XANO_TEST_LIVE=true` (só leitura), `XANO_TEST_ALLOW_WRITES=true` (grava) e `XANO_TEST_CONCURRENCY=true` (corridas), com `pytest -m integration` | Contratos contra um workspace real. Só a parte de leitura rodou ao vivo, em produção: como VENDEDOR em 2026-10-27 e 2026-11-14, com os 3 perfis em 2026-11-15 e com MECANICO e GERENTE em 2026-11-22. Os testes rodaram isolados e cadenciados (20 s entre eles) por causa do limite de taxa do plano Free | Escrita e corridas: nada sem um workspace de testes, e nunca rodaram. O limite é de cerca de 10 requisições por 20 s: `test_every_profile_reads_shared_resources` pausa 10 s entre perfis, porque com 3 s o terceiro ainda recebia 429 |
| XanoScript | Validador do MCP `xano-developer` e `xano workspace push -d ./xano --dry-run` | Sintaxe dos `.xs` e o diff que o push aplicaria | Nada é publicado só porque a CLI pede confirmação. Na CLI 1.3.3, se a instância responde "Push preview not yet available on this instance", o `--dry-run` segue para a confirmação de publicação. Por isso, **nunca** combine `--force` com `--dry-run`, e pare assim que a prévia não vier. O push exige o OK do usuário |
| Tipos | indisponível | — | — |

**Referência em 2026-11-22 (Change 16, de 2026-11-14, e correções até 2026-11-22; cada item traz a data da última execução):**

- ruff: sem violações;
- compileall: OK;
- pytest offline (`-m "not integration and not browser"`): 499 passaram e 47 foram desmarcados, 44 de integração e 3 de navegador, contados com `--collect-only` (2026-11-23, com a Change 18, os ajustes da revisão pós-entrega e o contrato do regex no stack). A execução sem `-m` não foi repetida;
- integração ao vivo, só leitura e em testes isolados:
  - VENDEDOR (2026-11-14): o detalhe de OS inexistente responde 404, a oficina e as entradas são lidas, a entrada de mercadoria é recusada com 403 e o carrinho com produto inexistente é recusado com 400 antes da transação;
  - 3 perfis (2026-11-15): VENDEDOR e MECANICO recebem 403 em fornecedores, funcionários e financeiro; o MECANICO também em motos do estoque e entrada de mercadoria. O GERENTE lê fornecedores, funcionários e o resumo financeiro, com o DTO validado e período inválido recusado com 400. Os 3 leem a oficina;
  - GERENTE (2026-11-18): com as primeiras entradas, `GET entrada_mercadoria` respondia `500 "Invalid expression"`. Depois da correção, respondeu 200 com 2 entradas, cada uma com `quantidade_itens` inteiro (3), aceito pelo DTO;
  - MECANICO (2026-11-22): `test_mechanic_cannot_sell_at_the_counter` passou com um produto ativo. A venda no balcão é recusada com 403 pelo `enforce_role`, o primeiro passo do endpoint, antes de qualquer gravação;
  - GERENTE (2026-11-22, 1 login e 2 leituras): o resumo de 360 dias trouxe 3 operações, da mais recente para a mais antiga, com o funcionário preenchido: 1 venda de balcão (2026-11-22 22:12) e 2 entradas de mercadoria (2026-11-18). A venda de balcão é posterior à publicação da correção de `vendas_POST.xs` (`28ddd3a`). A transação só é gravada depois do mapa de quantidades e da conferência do total, na mesma transação, então a venda prova que o endpoint corrigido rodou com dados; os itens dela não foram lidos. A lista de OS trouxe 1 OS aberta com autor e mecânico preenchidos pelos apelidos de join;
  - GERENTE (2026-11-22, depois do push de `Oficina/detalhe_os`; 1 login e 1 leitura): `GET ordens_servico/1` antes respondia `500 "Unable to locate var: transacao.id"`. Agora a OS aberta e não faturada responde 200, com os 26 campos e `id_transacao` e `data_lancamento` nulos, aceita pelo DTO. A mesma função monta a resposta de criar a OS, incluir ou remover item e mudar o status, que antes salvavam a alteração e mesmo assim respondiam 500. Essas 4 gravações não foram repetidas nesta leitura; o fechamento de OS, que é uma mudança de status, entrou na validação manual registrada abaixo;
  - Change 18 (2026-11-23, depois do push dos 3 endpoints de `admin/` e dos 5 `PATCH` dos cadastros, com `--dry-run` seguinte sem mudanças; bateria com ~2,5 s entre chamadas, 8 de 8 aprovadas):
    - **GERENTE:**
      - `GET admin/usuarios` respondeu 200 só com os campos permitidos, sem `password` nem `password_reset`;
      - `PATCH funcionarios/5` só com o `contato` (alterado e restaurado) e com `{"ativo": false}` e depois `{"ativo": true}` respondeu 200, e cada vez só o campo enviado mudou. Isso prova a correção D10 e que o `false` sobrevive a `filter_null|filter_empty_text`;
      - `auth/signup` criou o usuário de teste 5 para o "Funcionário Teste";
      - `POST admin/usuarios/5/senha` respondeu 200 com `{email, id, name}`, sem a senha;
      - `GET admin/eventos` respondeu 200 com `itemsTotal` e `pageTotal` (totais confirmados), e o evento mais recente era `admin_reset_password`, com `metadata` só com ids;
      - ao final, o "Funcionário Teste" ficou **inativo** e com o contato original, e o usuário de teste dele continua em produção sem acesso;
    - **VENDEDOR:** 403 nos 3 endpoints de `admin/`. O reset foi tentado contra o usuário de teste, nunca contra uma conta real;
    - as leituras do GERENTE e as recusas de VENDEDOR e MECANICO podem ser repetidas com `XanoLiveAdminReadTests`, opt-in e só de leitura, em `tests/test_integration_xano.py`, com `XANO_TEST_LIVE=true`. O reset desse teste aponta para o id inexistente 999999. A lógica foi conferida offline contra um servidor simulado, que acusou o vazamento de `password` e o 200 para o VENDEDOR. Os testes ainda não rodaram em produção;
  - regex no stack (2026-11-23). Contexto: o push dos 4 endpoints com `regex_matches` e `precondition` no lugar do filtro `pattern` (ver a lição em `docs/xano-api-client.md`), seguido de um `--dry-run` sem mudanças:
    - `POST motos` cadastrou as 3 unidades do povoamento (Breakout, Fat Boy e Sportster). A Sportster foi vendida a um cliente pelo VENDEDOR, com receita `MOTO` de R$ 79.900,00;
    - `PATCH motos/7` (a Breakout nova) só com o próprio chassi respondeu 200. Os 6 campos comparados (chassi, cor, ano, preço, status e modelo) ficaram iguais, e o `atualizado_em` mudou. Isso também prova o `pick:($raw_input|keys)` do `PATCH` de motos e o `Vendas/detalhe_moto` da resposta;
    - provas de recusa, montadas para não gravar nada mesmo se a validação falhasse:
      - `PATCH motos/999999999` com chassi inválido respondeu 400 "Chassi inválido: use os 17 caracteres do VIN, sem I, O e Q.". Se a validação falhasse, a resposta seria 404;
      - `POST modelos_moto` com o nome já usado "Fat Boy": com o hex válido `#0B0B0B`, a validação passou e a resposta foi "Já existe um modelo com esse nome."; com o hex inválido `#0B0B0G`, parou em "Use cores no formato #RRGGBB.". Continua havendo um só modelo "Fat Boy";
      - o `PATCH modelos_moto` tem o mesmo bloco de validação, mas não foi chamado ao vivo;
    - totais do povoamento no mês até hoje:
      - receitas: R$ 86.149,60 (MOTO R$ 79.900,00, ORDEM_SERVICO R$ 4.080,60 e BALCAO R$ 2.169,00);
      - despesas: R$ 11.840,60;
      - saldo: R$ 74.309,00;
      - motos em estoque: 8 (7 disponíveis e 1 reservada);
      - OS ativas: 2;
- `reflex compile --dry`: OK;
- validador do MCP `xano-developer`: 132 `.xs` válidos em 2026-11-23, incluindo os 3 de `/admin`, os 5 `PATCH` corrigidos e os 4 endpoints com regex no stack (129 em 2026-11-22, quando o MCP voltou). Entre 2026-11-18 e 2026-11-22 ele não conectava, e o mesmo validador (`@xano/developer-mcp` 2.2.6) rodou localmente em Node, a partir do pacote em cache;
- smoke de navegador: 3 passaram em 2026-11-17 e em 2026-11-18, antes do commit `f43e7ba`, contra o app local e com o catálogo público real. Cobre só o catálogo e o login: a oficina e o balcão foram medidos no Edge com páginas de dados fictícios, sem Xano;
- validação manual ponta a ponta no navegador, em produção, feita pelo usuário e informada em 2026-11-23: detalhe e fechamento de OS, detalhe de entrada e trava de moto reservada, concluídos. Não há registro automatizado nem evidência anexada além desse relato; o smoke automatizado continua cobrindo só o catálogo e o login.

**Tipos:** não há checker estático. As Vars e os componentes do Reflex são dinâmicos, então mypy ou pyright gerariam ruído antes de achar defeitos; as fronteiras externas já são validadas em runtime pelo pydantic. Vale revisitar se a camada `services/` crescer sem cobertura de testes.

## Lint: regras e medição

O gate usa o conjunto padrão do ruff, todo como erro, configurado em [ruff.toml](../ruff.toml).

**Primeira medição (2026-10-15):** 202 ocorrências em 15 regras. Foram corrigidas 32, mais 1 (`UP046`) que surgiu ao declarar o alvo Python 3.14 (na primeira medição; o alvo atual é 3.12). Nenhuma muda o comportamento no runtime em uso, mas o requisito mínimo subiu: `Self` e `datetime.UTC` exigem Python 3.11, e os genéricos PEP 695 do `TtlCache` exigem 3.12. Antes, a sintaxe do código era compatível com 3.11. As correções foram:

- imports e variável sem uso;
- `Callable` vindo de `collections.abc`;
- `datetime.UTC` e `re.IGNORECASE`;
- tupla no lugar de set iterado;
- compreensão de dict;
- concatenação de texto entre parênteses;
- desempacotamentos sem uso;
- `Self` no `__enter__`;
- `ClassVar` no cache de tokens da integração;
- genéricos PEP 695 no `TtlCache`.

Ficam fora do gate, com o motivo:

| Regra | Ocorrências | Motivo | Quando revisitar |
| --- | --- | --- | --- |
| `I001` ordem de imports | 52 | Adotar reformataria 52 arquivos sem efeito em comportamento | Se quiserem adotar: um commit só de formatação com `ruff check . --select I001 --fix` e remoção do ignore |
| `FURB157` `Decimal("120000")` | 55 | A forma em string é a convenção para valores monetários e evita confusão com frações | Não adotar |
| `RUF012` atributo de classe mutável | 44, todos em `*_state.py` | As variáveis de State do Reflex são declaradas como atributos de classe e copiadas por sessão; nos outros arquivos a regra continua valendo | Não adotar nos states |
| `SIM117` `with` aninhados | 15, todos em testes | Cada `patch` em sua linha fica mais legível | Não adotar |
| `N999` nome de módulo | 4 | O nome do pacote vem do `app_name` do Reflex | Não adotar |

Para remedir (o `--isolated` ignora o `ruff.toml`):

```bash
.venv/Scripts/ruff check . --isolated --target-version py312 --select I001,FURB157,SIM117,N999,RUF012 --statistics
```

## Regras de base

- Regras de UI (cores só em `styles/theme.py` e `assets/harley.css`, um único `status_badge`, contraste, foco e estados): [design-system.md](../openspec/specs/design-system.md).
- Fronteiras (o que se repete entre páginas fica em `ui_helpers.py` e `feedback.py`; os States não chamam `rx.toast` direto nem importam funções de outros States de página): [arquitetura-e-contratos.md](../openspec/specs/arquitetura-e-contratos.md).
- Integridade no Xano: papéis por `enforce_role`, operações críticas transacionais e idempotentes. Os contratos estáticos em `tests/` cobrem isso.
- Teto de referência de 350 linhas, que não é gate. Em 2026-10-15, 14 arquivos passavam dele. Os maiores eram:
  - `vendas_state.py` (991);
  - `workshop_state.py` (987);
  - `vendas_pages.py` (749);
  - `services/xano_client.py` (642).

  Refatorar por responsabilidade é uma change OpenSpec própria.

## Estratégia de testes

- **Testes offline (padrão):** simulam o `XanoClient` e exercitam os handlers como o Reflex os executa. Comportamento novo vem com teste do caminho feliz e das falhas relevantes; correção de bug vem com teste de regressão.
- **Contratos dos `.xs`:** leem o texto dos endpoints e protegem RBAC, transações e validações sem chamar o Xano.
- **Leitura tolerante (Change 15):** `tests/test_resiliencia_leitura.py` injeta JSON malformado pelo HTTP simulado. Confere que só o registro ruim some, que o log não traz valores, que cada tela isola sua fonte e que as mensagens separam rede, dados e erro interno. Um registro gravado fora do app (painel do Xano) é o caso a cobrir sempre que um DTO de leitura mudar. Para ver o efeito na tela, rode uma cópia do app fora do projeto, com um `.env` próprio apontando para um Xano simulado (o `env_file` do Reflex sobrescreve variáveis do processo), e instale os pacotes da cópia nela mesma. Não ligue o `node_modules` da cópia ao do projeto: o cache do Reflex guarda caminhos absolutos, a cópia reinstala os pacotes e pode gravar versões novas no projeto.
- **Integração e navegador:** são opt-in. Use um workspace ou branch de testes, porque a integração com escrita grava dados reais. O smoke lê o catálogo público do workspace configurado no `.env` e nunca faz login.
- **Sem cobertura automatizada:** fluxos autenticados no navegador, que só tiveram a validação manual de 2026-11-23, regressão visual e a integração ao vivo com escrita e concorrência.

## Débitos conhecidos

Itens que a Change 16 (arquivada em 2026-11-15) deixou abertos, porque dependem de dados ou de ambiente:

- **Testes com escrita e concorrência:** `XANO_TEST_ALLOW_WRITES=true` e `XANO_TEST_CONCURRENCY=true` nunca rodaram. Exigem um workspace ou branch de homologação, porque gravam dados reais e o plano Free publica em produção. Os cenários novos ainda não foram escritos: duas entradas com o mesmo documento, duas entradas com os mesmos produtos em ordens opostas, e uma entrada e uma venda de balcão do mesmo produto.
- **Expressão entre parênteses como valor de filtro:** a forma documentada (`map:($$|to_upper)`, `push:("…" ~ $x)`) continua em 13 pontos de 11 arquivos.
  - Comprovados (9):
    - `` `$input|pick:($raw_input|keys)` `` foi comprovado ao vivo em `PATCH funcionarios/{id}` em 2026-11-23, com payload parcial e com `{"ativo": false}`. A mesma cadeia aparece, idêntica, nos outros 4 `PATCH` corrigidos (clientes, fornecedores, motos de clientes e produtos);
    - o detalhe de entrada (`function/estoque/detalhe_entrada.xs`, 2 pontos) passou na validação manual de 2026-11-23;
    - o `pick` do `PATCH motos/{id}`, com cadeia própria (`unset`/`set`), e `function/vendas/detalhe_moto.xs` responderam 200 com dados em 2026-11-23 (ver "regex no stack" acima).
  - Sem prova ao vivo registrada (4):
    - o mesmo `pick` no `PATCH` de modelos;
    - o prazo da reserva (`motos_id_reserva_POST.xs`);
    - `generate_magic_link` (2 pontos, sem chamadas).
- **Comprovados pelo povoamento de 2026-11-23** (`scripts/seed_demo.py`):
  - os `POST` de fornecedores, produtos, clientes, motos de clientes e unidades à venda (`POST motos`, depois do regex no stack);
  - a venda de moto;
  - a entrada de mercadoria;
  - a venda de balcão, inclusive a repetição da `chave_venda`, que devolve o recibo sem nova baixa;
  - a OS completa: abertura, transições, peças, mão de obra e conclusão com receita.
- **Sem prova ao vivo:** o `pick:($raw_input|keys)` e o regex de cores do `PATCH` de modelos, que exigem escrita. A ordem do resumo, a venda de balcão, os nomes da oficina e a recusa do MECANICO foram comprovados em 2026-11-22 (ver a referência acima).

## Revisão após implementação ou correção

Ao concluir um ciclo de implementação ou correção, sugira de 3 a 8 ciclos posteriores de code review. A quantidade acompanha o risco: mudanças pequenas tendem a 3; Xano, RBAC, dados ou concorrência, ao topo da faixa. Use focos complementares e entregue um prompt de continuação preenchido. Essa faixa é convenção do projeto; revisões adicionais dependem de pedido do usuário.

Cada ciclo verifica o estado atual e o código conectado e registra achados com severidade, local e evidência. Correções autorizadas são reavaliadas com os checks afetados, e correções da mesma rodada não reiniciam a contagem. Termine com uma verificação integrada e os riscos residuais, sem criar ciclos artificiais.

## Dependências e entrega

- **pip-audit (2026-10-15):** 55 pacotes instalados no `.venv`, nenhuma vulnerabilidade conhecida. A contagem incluía o `pypdf`, que não constava dos requisitos e foi removido do `.venv` depois, por não ser usado. Para repetir: congele com `pip freeze` e rode `uvx pip-audit -r <arquivo> --no-deps --disable-pip`. As dependências JavaScript que o Reflex gera em `.web/` não foram auditadas.
- **Versões fixadas:** as listadas em `requirements.txt` são fixas, exceto `pydantic` (`>=2.7,<3`) e `python-dotenv` (`>=1.1.0`), que usam faixas. O `requirements-dev.txt` fixa pytest, ruff e playwright. As dependências secundárias não listadas seguem a resolução padrão do pip. Em 2026-10-15 eram `pydantic-core`, `annotated-types` e `typing-inspection` (runtime, via pydantic), `colorama`, `iniconfig` e `pluggy` (pytest), e `greenlet` e `pyee` (playwright).
- **Versões disponíveis e não adotadas:** reflex 0.10.0, pydantic 2.14.1, starlette 1.8.0, granian 2.8.4. O Reflex fixa as próprias dependências; atualizar é uma change própria, com changelog e a suíte completa.
- **Checks explícitos:** não há CI, hooks Git nem bloqueios de branch. Atualize este documento junto dos comandos e regras que mudarem.
