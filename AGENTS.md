<!-- reflex managed begin (do not edit inside this block; add custom content outside the markers) -->
# Agents

This project uses the **Reflex agent skills** � up-to-date knowledge for building full-stack Python web apps with [Reflex](https://reflex.dev). Install them first, then use them as described below.

## Installing the Skills

Before working on this project, make sure the Reflex skills are available to you.

### Claude Code

If the skills are not already available, install them yourself by running these shell commands:

```bash
claude plugin marketplace add reflex-dev/agent-skills
claude plugin install reflex@reflex-agent-skills
```

Newly installed plugins load on the next session. After installing, tell the user to restart the session so the skills auto-load; until then, read the skill files directly from `~/.claude/plugins/` when you need them.

### Other agents (Cursor, OpenCode, Codex, Pi)

```
npx skills add reflex-dev/agent-skills
```

Or clone https://github.com/reflex-dev/agent-skills and copy the `skills/` folders into your agent's skill directory (see the repo README for paths).

### Verifying

Before writing or editing any Reflex code, confirm these three skills are available: `reflex-docs`, `setup-python-env`, and `reflex-process-management`. If they are not, STOP and run the install step above � do not proceed without them.

## Using the Skills

### Reflex documentation

For anything about Reflex APIs � components, state management, events, styling, database, routing, authentication � use the **reflex-docs** skill rather than relying on memory. It carries current, version-accurate docs.

### Initializing a new Reflex project

When starting a new Reflex project or setting up a development environment, you **must** follow the **setup-python-env** skill before doing anything else.

Do not skip any steps. Do not assume a virtual environment or Reflex is already available � always verify first by following the skill's instructions in order.

After the environment is ready and Reflex is installed, run:

```bash
reflex init
```

Then proceed with the user's request.

### Managing a Reflex process

When you need to compile, run, reload, or debug a Reflex application, follow the **reflex-process-management** skill for the correct sequence and error investigation steps.
<!-- reflex managed end -->

# Instruções para Agentes de IA

HarleyStore: gestão de concessionária e oficina Harley-Davidson (vitrine e venda de motos, balcão de peças, estoque, ordens de serviço, financeiro e acesso por cargo). Produto em `docs/project-overview.md`; entrada e mapa dos documentos em `README.md`.

## Stack

- Frontend em Reflex 0.9.12 no pacote `Projeto_HarleyStore/`. Requer Python >= 3.12 (o código usa genéricos PEP 695); o `.venv` usa 3.14.
- Versões fixas em `requirements*.txt`, exceto `pydantic` e `python-dotenv`, que usam faixas. As dependências secundárias não listadas (como `pydantic-core` ou as do pytest e do playwright) seguem a resolução padrão do pip.
- Backend, persistência, autenticação e regras no Xano, versionado em `xano/` (XanoScript). O workspace está no plano Free: **todo push vai direto para produção**.
- Mudanças funcionais pelo OpenSpec (`openspec/`), escritas em português brasileiro.

## Comandos canônicos

Rode na raiz com o `.venv`; os caminhos funcionam no PowerShell e no Git Bash. Variáveis de ambiente (`HARLEY_BROWSER_URL`, `XANO_TEST_*`) mudam de sintaxe: `VAR=valor comando` no Git Bash; no PowerShell, a variável persiste no processo até ser removida.

- Variáveis que não alteram estado (`HARLEY_BROWSER_URL`, `XANO_TEST_LIVE`): linha única, `$env:VAR='valor'; comando; Remove-Item Env:VAR`.
- Variáveis que gravam no Xano (`XANO_TEST_ALLOW_WRITES`, `XANO_TEST_CONCURRENCY`): sempre `try`/`finally`, para limpar mesmo após erro ou Ctrl+C. Por exemplo, `try { $env:XANO_TEST_ALLOW_WRITES='true'; .venv/Scripts/python -m pytest -m integration } finally { Remove-Item Env:XANO_TEST_ALLOW_WRITES }`. Com `XANO_TEST_CONCURRENCY`, remova as duas no `finally`. Se uma delas ficar ativa, o próximo `pytest` comum grava no Xano de produção.

O que cada check prova: `docs/quality.md`.

| Objetivo | Comando |
| --- | --- |
| Instalar | `python -m venv .venv` e `.venv/Scripts/python -m pip install -r requirements-dev.txt` |
| Desenvolver | `.venv/Scripts/reflex run` (frontend na porta 3000), seguindo a skill `reflex-process-management` |
| Lint | `.venv/Scripts/ruff check .` |
| Sintaxe | `.venv/Scripts/python -m compileall -q Projeto_HarleyStore tests rxconfig.py` |
| Testes | `.venv/Scripts/python -m pytest` (integração com o Xano e navegador são opt-in) |
| Build | `.venv/Scripts/reflex compile --dry` |
| Tipos | indisponível; motivo em `docs/quality.md` |
| XanoScript | validador do MCP `xano-developer`; prévia com `xano workspace push -d ./xano --dry-run` |
| Verificar base | lint, sintaxe, testes e build, nessa ordem |

## Regras do projeto

- Antes de alterações significativas, consultar `docs/` e `openspec/` (requisitos vigentes em `openspec/specs/`).
- Frontend exclusivamente em Reflex, com os mecanismos próprios de componentes, State, eventos e páginas. Outra tecnologia de frontend exige alteração arquitetural aprovada.
- Alterações funcionais usam o fluxo do OpenSpec.
- Reutilizar o código existente e evitar duplicação de funções.
- Não alterar funcionalidades não relacionadas com a tarefa atual sem justificativa.
- Xano: `xano auth` é feito só pelo usuário, no terminal dele. Push somente depois de um `--dry-run` revisado e do OK explícito do usuário. Mudança de banco precisa de OK antes de editar e de novo antes do push.
- Nunca exibir valores do `.env` nem credenciais de teste.
- Commit e push ficam com o usuário, salvo pedido explícito.

## Acordos de trabalho

- Ler instruções e código pertinentes antes de editar; separar observação, hipótese, decisão e evidência.
- Definir aceite e comandos antes de implementar. Testar comportamento e falhas relevantes; correção de bug vem com reprodução e teste de regressão quando viável.
- Menor mudança completa (Ponytail full): sem abstrações, opções ou dependências não pedidas, preservando validação, tratamento de erros, segurança e acessibilidade.
- Não apresentar hipótese como fato nem integração pendente como resultado.
- Atualizar o documento responsável junto com mudanças de comportamento, comando, schema, fronteira ou configuração.
- Responder perguntas de status e continuar o trabalho autorizado. Um bloqueio afeta só o que depende dele. Respeitar pausas e negativas; não prometer execução em segundo plano sem processo verificável. Na retomada, conferir Git, arquivos e processos reais antes de confiar num resumo.
- Publicação, mensagens a terceiros, custos e ações destrutivas dependem de autorização específica.

## Ferramentas

- Reflex: skills do bloco acima. XanoScript: skill `xanoscript-docs-expert` e MCP `xano-developer`.
- Context7 (configurado em `.mcp.json` e `.codex/config.toml`) para as demais bibliotecas: resolver o identificador e consultar um conceito por vez, sem enviar segredos ou código privado. Se estiver indisponível, usar a documentação oficial e registrar a limitação.
- Graphify: grafo só de código em `graphify-out/` (fora do Git), atualizado com `GRAPHIFY_NO_AUTO_REFRESH=1 graphify update .` (no PowerShell, `$env:GRAPHIFY_NO_AUTO_REFRESH='1'; graphify update .`). Sem essa variável, o graphify pode reescrever a skill instalada fora do projeto. O grafo pode estar desatualizado; confirmar no código.
- Superpowers está desativado neste projeto por decisão do usuário: conduzir o design (classificação, uma pergunta por vez, aprovação antes de editar) manualmente.
- Navegador: o smoke Playwright com o Edge (`docs/quality.md`) roda contra o app local em `http://localhost:3100`. O backend é o Xano de produção, então o smoke só lê dados públicos do catálogo, sem login, sem sessão e sem gravar nada. Nunca apontar para o app publicado nem usar sessão pessoal.
- O projeto não tem hooks de agente, RTK, hooks Git nem bloqueios de branch; não criá-los sem pedido. Estado das integrações e pendências: `docs/setup.md`.

## Delegação e revisão

- Delegar só quando isolar contexto, especializar ou paralelizar trabalho independente compensar a coordenação. Usar o modelo mais leve capaz do aceite (busca e inventário: leve; implementação delimitada: intermediário; segurança, RBAC, dados, concorrência e Xano: o mais capaz), preservando o modelo principal.
- Cada tarefa delegada recebe objetivo, contexto mínimo, arquivos permitidos, aceite e checks. Um escritor por arquivo; revisores só leem; o coordenador confere diff e checks.
- Após cada ciclo de implementação ou correção, sugerir de **3 a 8 ciclos de code review** conforme risco e tamanho, com o motivo e um prompt copiável com focos e comandos reais. É convenção do projeto, não garantia de qualidade, e a sugestão não autoriza executar as rodadas.
