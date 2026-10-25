# Setup das ferramentas de IA e evidências

## Origem e contexto

- **Data:** 2026-10-15.
- **Toolkit:** [vibe-coding-toolkit](https://github.com/soumatheusgomes/vibe-coding-toolkit) na revisão `f13bb35` (`main`), com o prompt 12 (projeto existente). Usado a partir de um clone temporário, fora do projeto.
- **Projeto:** Reflex 0.9.12, com requisito mínimo de Python >= 3.12 (genéricos PEP 695); desenvolvimento e execução em Python 3.14.7. Backend Xano no plano Free.
- **Dependências:** pip, com as versões listadas em `requirements*.txt` fixas, exceto `pydantic` e `python-dotenv` (faixas em `requirements.txt`). As dependências secundárias não listadas seguem a resolução padrão do pip.
- **Clientes:**
  - Claude Code 2.1.296, com o modelo principal preservado;
  - Codex, só como app desktop (não há CLI no PATH).
- **Escopo autorizado:** somente o projeto. Nada global foi instalado ou configurado. Fora do projeto ficaram:
  - os caches do uv e do pip;
  - uma entrada da auto-memória do Claude Code, gravada pelo próprio sistema de memória em `~/.claude/projects/<projeto>/memory/codex-import-rewrites-claude.md`, com o ponteiro no `MEMORY.md`. Ela registra a reescrita "claude"→"Codex" feita pelo importador do Codex.
- **Subagentes:** a política está em [AGENTS.md](../AGENTS.md#delegação-e-revisão). Este setup não usou nenhum: as etapas eram sequenciais e pequenas o bastante para execução direta.
- **Fontes consultadas:** os guias do toolkit nessa revisão; o Context7 (ruff e Playwright Python); o `--help` das CLIs (graphify 0.9.82, reflex, `claude plugin`); e o código do graphify instalado, que mostrou que `graphify update` não chama LLM.

## Decisões

Cada uma foi tomada pelo usuário no brainstorming de 2026-10-15:

| Decisão | Motivo | Revisitar quando |
| --- | --- | --- |
| Somente alterações no projeto | O prompt 12 não deve virar atualização geral da máquina | No setup da máquina (prompt 10) |
| ruff com medição antes do gate | O projeto não tinha lint | Ao adotar `I001` ou outra regra fora do gate |
| Playwright Python + Edge instalado, smoke opt-in | Validação de UI reproduzível sem baixar navegador e sem global | Quando houver credenciais de teste (fluxos autenticados) |
| Caveman considerado coberto pelo Ponytail full | O Ponytail já exige respostas curtas | Se as respostas continuarem prolixas |
| Superpowers continua desativado no projeto | Decisão anterior do usuário; o protocolo de design é feito à mão | A pedido do usuário |
| Documentos equivalentes mapeados, sem criar fontes concorrentes | Já existiam documentos canônicos | — |
| Sem CI, script composto ou atualização de dependências | Não havia CI a integrar; o Reflex fixa as próprias dependências | Numa change própria |

## Mapeamento dos documentos

| Destino do toolkit | No projeto | Ação |
| --- | --- | --- |
| `README.md` | [README.md](../README.md) | Criado |
| `PRODUCT.md` | [project-overview.md](project-overview.md) | Mantido como fonte |
| `AGENTS.md` | [AGENTS.md](../AGENTS.md) | Seção do projeto conciliada com o template; bloco gerenciado do Reflex intacto |
| `CLAUDE.md` | [CLAUDE.md](../CLAUDE.md) | Já importava `@AGENTS.md`; inalterado |
| `docs/architecture.md` | [project-structure.md](project-structure.md), [arquitetura-e-contratos.md](../openspec/specs/arquitetura-e-contratos.md), [domain-model.md](domain-model.md), [xano-api-client.md](xano-api-client.md), [xano-auth-mapping.md](xano-auth-mapping.md) | Mantidos como fonte |
| `docs/design.md` | [design-system.md](../openspec/specs/design-system.md) | Mantido como fonte |
| `docs/onboarding.md` | [onboarding.md](onboarding.md) | Criado |
| `docs/quality.md` | [quality.md](quality.md) | Criado |
| `docs/setup.md` | este documento | Criado |

## Componentes

Estados possíveis:

- **validado:** executado e observado;
- **configurado:** feito, mas sem execução;
- **reaproveitado:** um equivalente que já existia;
- **inaplicável:** com o motivo;
- **bloqueado:** com a condição para retomar.

| Componente | Ação e motivo | Escopo | Estado e evidência |
| --- | --- | --- | --- |
| Ponytail 5.1.0 | Já instalado no Claude e no Codex | Usuário | Reaproveitado; ativo nas sessões do setup |
| Superpowers 6.4.2 | Mantido desativado por decisão do usuário | Projeto (`.claude/settings.local.json`) | Reaproveitado (o protocolo foi feito à mão) |
| Caveman | Coberto pelo Ponytail full | — | Inaplicável por equivalente |
| Subagentes | Política no AGENTS.md | Projeto | Configurado; nenhum usado |
| RTK | Exige binário global e `rtk init --global`, que altera `~/.claude/settings.json` | Usuário | Bloqueado: retomar no prompt 10 com autorização, conferindo a convivência com os hooks habblaud e ponytail |
| Context7 (Claude) | `.mcp.json` com o servidor remoto, sem chave | Projeto | Validado: ferramentas carregadas na sessão da extensão do VS Code e consulta real a `/websites/astral_sh_ruff`; o endpoint responde como Context7 4.4.1. Na CLI `claude` do terminal, o servidor ainda aparece como "Pending approval" |
| Context7 (Codex) | `.codex/config.toml` | Projeto | Configurado: TOML válido; falta confiar no projeto e consultar numa conversa Codex |
| Graphify 0.9.82 | `.graphifyignore` + `graphify update .` (só AST, sem LLM) | Projeto | Validado: 2750 nós, 7684 arestas, 158 comunidades; `explain carrossel_fotos` e `query` acham código das Changes 11–13. Limite: os 131 `.xs` de `xano/` não são suportados e ficam fora do grafo |
| Graphify no Codex | O `~/.codex/AGENTS.md` aponta para `~/.Codex/skills/graphify`, que não existe | Usuário | Bloqueado: `graphify install --platform codex` é global; retomar no prompt 10 |
| find-skills | A cópia em `.agents/skills/` estava alterada ("claude" trocado por "Codex", provável importador do Codex) e ignorada pelo `.gitignore`. Foi restaurada a partir de `.claude/skills/` e o ignore saiu | Projeto | Validado: as duas cópias têm o mesmo sha256 e a skill é descoberta pelo Claude |
| Skills Reflex | Plugin no Claude e no Codex, mais cópias em `.agents/` e `.aider-desk/` | Usuário + projeto | Reaproveitado; no Codex aparecem duplicadas (plugin e `.agents/`) |
| MCP do plugin reflex | Precisa de autenticação | Usuário | Bloqueado: o usuário autentica pelo `/mcp` |
| MCP xano-developer | Developer MCP do manual (documentação e validação, sem token). Em 2026-10-22 entrou também em `.mcp.json` e `.codex/config.toml`, com o mesmo nome da configuração do usuário para não duplicar e `cmd /c` porque o `npx` do Windows é um `.cmd`. O editor e o Gemini usam `.vscode/mcp.json` e `.gemini/settings.json`, como no manual | Projeto + usuário + editor | Validado: `claude mcp list` mostra um único `xano-developer` conectado (vale o do usuário até o do projeto ser aprovado), e o validador aprovou os 129 `.xs` |
| web-design-guidelines | Já instalada | Usuário | Reaproveitado para revisão de UI |
| Skills Vercel React/Next e mobile | O frontend é escrito em Python; o React é gerado em `.web/` | — | Inaplicável |
| writing-guidelines | Guia em inglês e voltado à Vercel; os docs são em pt-BR | — | Inaplicável |
| Navegador | `playwright==1.64.0` com `channel="msedge"`, em [test_browser_smoke.py](../tests/test_browser_smoke.py) com marcador `browser` | Projeto | Validado: 2 testes passaram em 5 rodadas seguidas contra o app em `:3100` |
| agent-browser | Instalação global; o Playwright cobre a necessidade | — | Bloqueado/inaplicável; retomar no prompt 10 se faltar algo |
| Chrome DevTools MCP | Chrome não está instalado; console e erros já são cobertos pelo smoke | — | Inaplicável até haver investigação de desempenho ou rede |
| Anthropic skills | skill-creator e frontend-design já instaladas. `webapp-testing` duplicaria o smoke; document-skills, claude-api e mcp-builder sem uso | Usuário | Reaproveitado / inaplicável |
| aia-harness | Duplicaria este harness | — | Inaplicável |
| Plugins oficiais do Claude | O `/code-review` já vem embutido | — | Inaplicável |
| Hooks do cliente | Nenhum criado; habblaud e ponytail preservados | — | Reaproveitado |
| Obsidian | Sem vault nem necessidade | — | Inaplicável |
| Memória do Claude | Auto-memória com índice curto | Usuário | Reaproveitado |
| ruff 0.17.0 | Gate com o conjunto padrão e alvo `py312`, o requisito mínimo; 5 regras fora dele, com motivo ([quality.md](quality.md#lint-regras-e-medição)) | Projeto | Validado: `ruff check .` sem violações; a medição fora do gate é igual com alvo 3.12 ou 3.14 (170 ocorrências) |
| Tipos | Vars do Reflex geram ruído; pydantic valida em runtime | — | Inaplicável (motivo em [quality.md](quality.md)) |
| ESLint/Biome, templates `next/` e `eslint/` | Não há JavaScript escrito à mão | — | Inaplicável |
| pip-audit | Pacotes instalados no `.venv` | Temporário (uv) | Validado: 55 pacotes, nenhuma vulnerabilidade conhecida. A contagem incluía o `pypdf`, fora dos requisitos e removido depois por não ser usado |
| CI | Não existe; criar seria infraestrutura nova | — | Inaplicável |
| `templates/rules`, `settings.json.example`, `hooks/` | Nenhum papel recorrente nem hook necessário | — | Inaplicável |

## Alterações no projeto

**Criados:**

- `README.md`, `docs/onboarding.md`, `docs/quality.md`, `docs/setup.md`;
- `ruff.toml`, `.graphifyignore`, `.mcp.json`, `.codex/config.toml`;
- `tests/test_browser_smoke.py`;
- `.agents/skills/find-skills/SKILL.md`, que passa a ser versionado.

**Alterados:**

- `AGENTS.md` (seção do projeto), `docs/project-structure.md` (passo de validação) e `docs/xano-api-client.md` (aviso de deploy sobre o placeholder);
- `.gitignore`: saiu a linha `.agents/skills/` e entrou `reflex.log`;
- `requirements-dev.txt` (ruff e playwright) e `pytest.ini` (marcador `browser`);
- `xano/api/harley/harley.xs`: o token do Swagger virou o placeholder `YOUR_XANO_SWAGGER_TOKEN`, e o arquivo entrou no `.graphifyignore`.

**Correções de lint** (sem mudar comportamento no runtime em uso, mas o requisito mínimo subiu para Python >= 3.12):

- 5 módulos do app:
  - `cadastros_state.py`;
  - `ui_helpers.py`;
  - `vendas_state.py`;
  - `services/catalogo.py`;
  - `services/xano_client.py`.
- 15 arquivos de teste.

## Verificações

| Check | Antes do setup | Depois |
| --- | --- | --- |
| `ruff check .` | não existia (202 ocorrências com as regras padrão) | sem violações; 170 fora do gate, documentadas |
| `compileall` | 72 arquivos OK | 73 arquivos OK |
| `pytest` | 403 passaram, 39 pulados | 403 passaram, 41 pulados (os 2 a mais são o smoke opt-in) |
| `reflex compile --dry` | OK | OK |
| `pip check` | OK | OK |
| Smoke de navegador | não existia | 2 passaram, 5 rodadas seguidas |
| pip-audit | não existia | nenhuma vulnerabilidade |
| Links dos docs criados ou alterados | — | sem links quebrados; `git diff --check` limpo |

**Recursos temporários:** o app subiu em `:3100` só para o smoke, com log no scratchpad da sessão. O servidor e os processos filhos foram encerrados, e a porta foi conferida livre. Dois pulls antigos do workspace Xano, guardados no scratchpad durante o audit e contendo o token real do Swagger, foram apagados com autorização do usuário.

**Reexecução sem duplicar:**

- o context7 aparece uma só vez em `claude mcp list`;
- `graphify update` é incremental;
- nenhum hook foi criado;
- as skills não se repetem no Claude.

**Só revisão estática:** a descoberta pelo Codex (AGENTS.md, `.codex/config.toml`, skills de `.agents/`).

**Interrupção:** a conexão caiu durante o smoke (`ERR_INTERNET_DISCONNECTED`). A execução foi retomada após conferir o Git e os processos, e o smoke foi revalidado.

## Pendências e próxima ação

| Pendência | Causa | Próxima ação |
| --- | --- | --- |
| Token do Swagger do grupo `HARLEY` exposto | Estava versionado em texto puro e apareceu na saída de uma sessão de revisão. O arquivo agora tem o placeholder `YOUR_XANO_SWAGGER_TOKEN`, mas o valor real continua no histórico do Git | Usuário: desligar o Swagger público (`xano workspace edit --no-swagger`) ou gerar um token novo antes do próximo push de `xano/`; ver o aviso em [xano-api-client.md](xano-api-client.md) |
| `harley.xs` fora do `.gitignore` | O arquivo é versionado e é a fonte do grupo `HARLEY` no push. O `.gitignore` não afeta arquivos já rastreados, e tirá-lo do Git faria um clone novo publicar sem o grupo (um `--sync --delete` o removeria do workspace) | Decisão do usuário: incluir mesmo assim ou manter só no `.graphifyignore` |
| Context7 e AGENTS no Codex | Não há CLI para testar daqui | Usuário: confiar no projeto no Codex e pedir uma consulta de documentação |
| Context7 na CLI `claude` | Servidor do projeto ainda não aprovado no terminal | Usuário: aprovar quando o `claude` pedir |
| MCP do plugin reflex | Exige login | Usuário: `/mcp` |
| RTK, graphify no Codex, agent-browser | Instalação global, fora do escopo autorizado | Prompt 10, com autorização |
| `~/.codex/AGENTS.md` com o caminho `~/.Codex/skills/graphify` | Provável importador do Codex trocando "claude" por "Codex" | Corrigir no prompt 10 (`graphify install --platform codex`) |
| "�" no bloco gerenciado do Reflex no AGENTS.md | Travessão gravado com encoding errado | Não editado, por respeito ao marcador "do not edit"; um `reflex init` futuro pode regenerar o bloco |
| Colunas de `modelos_moto` só no Xano publicado | `galeria` (`image[1:10]`) e `default_motos` (texto) foram criadas pelo painel e nunca entraram em `xano/table/modelos_moto.xs` (comparação de 2026-10-22). O `--dry-run` de um push completo lista dois `DROP_FIELD` em `modelos_moto` (2026-10-25) | Decisão do usuário: versionar (e levar à vitrine numa change) ou remover. Até lá, push só com `-i` nos arquivos alterados e nenhum `--sync` |
| Specs do OpenSpec fora do layout da CLI | O archive foi padronizado em 2026-10-25: as 20 changes arquivadas estão em `openspec/changes/archive/AAAA-MM-DD-<nome>/`, como a CLI e o material do curso esperam (data do commit em que entraram no archive). As specs continuam em `openspec/specs/*.md`, e a CLI 1.13.2 só as acha em `openspec/specs/<capacidade>/spec.md` (`openspec list --specs` responde "No specs found"). Os workflows `/opsx` não estão instalados | Decisão do usuário: manter as specs como estão ou migrá-las numa change de estrutura |
| Débitos do audit no Xano | Mudanças no Xano exigem dupla aprovação e push | Changes próprias. Itens: agente e tool de IA remotos (`--sync --delete`), `\|sort` ambíguo em `entrada_mercadoria_POST` e `Financeiro/resumo_operacoes`, Swagger público, integração nunca rodada ao vivo (os modais sem Esc nem foco preso foram resolvidos na Change 14) |
| 14 arquivos acima de 350 linhas | Refatorar não cabe num setup | Change OpenSpec própria (prompt 09 do toolkit) |
| reflex 0.10.0 e outras atualizações | Pode trazer quebras | Change própria, com changelog e a suíte completa |

## Manutenção

- **Repetir o setup:** cole o atalho do prompt 12. Ele confere a revisão do toolkit, compara com este documento e preserva as personalizações.
- **Grafo:** depois de mudar código, `GRAPHIFY_NO_AUTO_REFRESH=1 graphify update .`.
- **Skills do projeto:** `npx --yes skills@latest update --project --yes`, revisando o diff e o `skills-lock.json`.
- **Lint e dependências:** remedir as regras fora do gate e repetir o pip-audit com os comandos de [quality.md](quality.md).

**Revisão sugerida para este setup: 4 ciclos.** São sobretudo docs e configuração, mas há correções mecânicas em 5 módulos do app e um teste novo, então fica acima do mínimo. Prompt de continuação:

```text
Faça 4 ciclos de code review do diff atual do setup do toolkit (git diff e arquivos não versionados), sem aplicar correções sem minha autorização:
1) AGENTS.md, README.md e docs/{onboarding,quality,setup}.md: fatos conferidos contra o código e os comandos, links válidos, nada planejado descrito como pronto;
2) regressões das correções de lint (cadastros_state.py, ui_helpers.py, vendas_state.py, services/catalogo.py, services/xano_client.py e testes) e do tests/test_browser_smoke.py;
3) segurança e configuração: .mcp.json, .codex/config.toml, ruff.toml, .graphifyignore, .gitignore e requirements-dev.txt — nada de segredo versionado e exclusões corretas;
4) integração: rode .venv/Scripts/ruff check ., .venv/Scripts/python -m compileall -q Projeto_HarleyStore tests rxconfig.py, .venv/Scripts/python -m pytest, .venv/Scripts/reflex compile --dry e o smoke (app com reflex run --env prod --single-port --backend-port 3100; depois HARLEY_BROWSER_URL=http://localhost:3100 .venv/Scripts/python -m pytest -m browser no Git Bash, ou $env:HARLEY_BROWSER_URL='http://localhost:3100'; .venv/Scripts/python -m pytest -m browser; Remove-Item Env:HARLEY_BROWSER_URL no PowerShell).
Apresente achados com severidade, arquivo:linha, evidência e correção proposta.
```
