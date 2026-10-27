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
| Integração (opt-in) | `XANO_TEST_LIVE=true` (só leitura), `XANO_TEST_ALLOW_WRITES=true` (grava) e `XANO_TEST_CONCURRENCY=true` (corridas), com `pytest -m integration` | Contratos contra um workspace real | Nada sem um workspace de testes; nunca foi rodada ao vivo |
| XanoScript | Validador do MCP `xano-developer` e `xano workspace push -d ./xano --dry-run` | Sintaxe dos `.xs` e o diff que o push aplicaria | Nada é publicado; o push exige o OK do usuário |
| Tipos | indisponível | — | — |

**Referência em 2026-10-27 (Change 17: fotos das motos vindas do Xano):**

- ruff: sem violações;
- compileall: OK;
- pytest: 437 passaram, 42 pulados (integração e navegador);
- `reflex compile --dry`: OK;
- smoke de navegador: 3 passaram, com o catálogo público real;
- validador do MCP `xano-developer`: 129 `.xs` válidos.

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
- **Sem cobertura:** fluxos autenticados no navegador, regressão visual e a integração ao vivo.

## Revisão após implementação ou correção

Ao concluir um ciclo de implementação ou correção, sugira de 3 a 8 ciclos posteriores de code review. A quantidade acompanha o risco: mudanças pequenas tendem a 3; Xano, RBAC, dados ou concorrência, ao topo da faixa. Use focos complementares e entregue um prompt de continuação preenchido. Essa faixa é convenção do projeto; revisões adicionais dependem de pedido do usuário.

Cada ciclo verifica o estado atual e o código conectado e registra achados com severidade, local e evidência. Correções autorizadas são reavaliadas com os checks afetados, e correções da mesma rodada não reiniciam a contagem. Termine com uma verificação integrada e os riscos residuais, sem criar ciclos artificiais.

## Dependências e entrega

- **pip-audit (2026-10-15):** 55 pacotes instalados no `.venv`, nenhuma vulnerabilidade conhecida. A contagem incluía o `pypdf`, que não constava dos requisitos e foi removido do `.venv` depois, por não ser usado. Para repetir: congele com `pip freeze` e rode `uvx pip-audit -r <arquivo> --no-deps --disable-pip`. As dependências JavaScript que o Reflex gera em `.web/` não foram auditadas.
- **Versões fixadas:** as listadas em `requirements.txt` são fixas, exceto `pydantic` (`>=2.7,<3`) e `python-dotenv` (`>=1.1.0`), que usam faixas. O `requirements-dev.txt` fixa pytest, ruff e playwright. As dependências secundárias não listadas seguem a resolução padrão do pip. Em 2026-10-15 eram `pydantic-core`, `annotated-types` e `typing-inspection` (runtime, via pydantic), `colorama`, `iniconfig` e `pluggy` (pytest), e `greenlet` e `pyee` (playwright).
- **Versões disponíveis e não adotadas:** reflex 0.10.0, pydantic 2.14.1, starlette 1.8.0, granian 2.8.4. O Reflex fixa as próprias dependências; atualizar é uma change própria, com changelog e a suíte completa.
- **Checks explícitos:** não há CI, hooks Git nem bloqueios de branch. Atualize este documento junto dos comandos e regras que mudarem.
