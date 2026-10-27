# Preparação local

## Pré-requisitos

- Windows com PowerShell ou Git Bash, o ambiente em uso. Em Linux ou macOS, troque `.venv/Scripts/` por `.venv/bin/`.
- Python >= 3.12, porque o código usa genéricos PEP 695 (`class TtlCache[T]`). O desenvolvimento e a execução usam 3.14 (o `.venv` atual tem 3.14.7).
- Na primeira compilação, o Reflex baixa o Bun em `$env:LOCALAPPDATA\reflex\bun` (caminho no PowerShell) e instala os pacotes JavaScript em `.web/`.
- Microsoft Edge, apenas para o smoke de navegador (o Playwright usa o Edge instalado e não baixa navegador).
- CLI do Xano (`xano --version`), apenas para publicar o backend.

## Primeira execução

1. Crie o ambiente e instale as dependências. As versões listadas são fixas, exceto `pydantic` e `python-dotenv` (faixas em `requirements.txt`). As dependências secundárias não listadas (como `pydantic-core` ou o `greenlet` do playwright) seguem a resolução padrão do pip.

   ```bash
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements-dev.txt
   ```

2. Copie `.env.example` para `.env` e preencha as URLs do workspace: `XANO_API_BASE_URL` (grupo `HARLEY`) e `XANO_AUTH_API_BASE_URL` (grupo `Authentication`). Ambas aparecem no painel do Xano como base URL de cada grupo de API. Em desenvolvimento, `XANO_AUTH_COOKIE_SECURE=false`. O `.env` não é versionado; não cole seu conteúdo em chats ou logs.
3. Inicie com `.venv/Scripts/reflex run`. O frontend abre em `http://localhost:3000`. A vitrine `/catalogo` é pública; as demais páginas pedem login de um funcionário cadastrado no Xano.

## Banco (Xano)

Não há banco local: dados, regras e autenticação vivem no workspace Xano, e `xano/` guarda a fonte versionada. No plano Free, um push vai direto para produção. O fluxo é:

1. Editar `xano/`.
2. Validar com o MCP `xano-developer`.
3. Rodar `xano workspace push -d ./xano --dry-run` e revisar.
4. Publicar só com o OK do responsável pelo workspace.

`xano auth` é feito pelo dono do workspace, no próprio terminal. Comandos, `--sync` e checklists de cada change estão em [xano-api-client.md](xano-api-client.md).

Os testes de integração gravam dados reais quando `XANO_TEST_ALLOW_WRITES=true`; use um branch ou workspace de testes.

## Verificar

Rode lint, sintaxe, testes e build, conforme a tabela de [AGENTS.md](../AGENTS.md#comandos-canônicos). O que cada um prova e os resultados esperados estão em [quality.md](quality.md). Sem um `.env` real, a suíte local passa e a integração com o Xano é pulada.

## Agentes

Leia [AGENTS.md](../AGENTS.md); o [CLAUDE.md](../CLAUDE.md) importa as mesmas instruções. Skills, MCPs, escopos e pendências estão em [setup.md](setup.md).

Na primeira sessão depois do setup, aprove os servidores `context7` e `xano-developer` do projeto. No Claude Code, isso aparece como pedido de aprovação dos MCPs do `.mcp.json`; no Codex, como confiança no projeto.

## Dificuldades conhecidas

- **Porta 3000 continua ocupada depois de encerrar o servidor no Windows:** um processo filho `multiprocessing-fork` pode continuar ativo. Encerre-o também.
- **Login responde 404:** falta `XANO_AUTH_API_BASE_URL`, e os grupos de API do workspace têm URLs diferentes.
- **O `--dry-run` sempre lista `UPDATE table modelos_moto`:** é uma diferença cosmética do padrão de `destaque`, explicada em [xano-api-client.md](xano-api-client.md).
- **O compile avisa que o WSL é recomendado:** é só aviso; o projeto roda no Windows nativo.
