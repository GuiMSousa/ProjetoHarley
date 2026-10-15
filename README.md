# HarleyStore

Sistema de gestão para concessionária e oficina Harley-Davidson: vitrine pública de motos, reservas e vendas, venda de peças no balcão, estoque com entradas de fornecedores, ordens de serviço da oficina e fechamento financeiro, com acesso por cargo (gerente, vendedor e mecânico).

O frontend é [Reflex](https://reflex.dev) 0.9.12 (Python) no pacote `Projeto_HarleyStore/`. Backend, banco, autenticação e regras de negócio ficam no [Xano](https://www.xano.com), com a fonte versionada em `xano/`.

## Executar

Requer Python >= 3.12 (o ambiente de desenvolvimento usa 3.14) e as URLs de um workspace Xano.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env   # preencha as URLs do Xano
.venv/Scripts/reflex run
```

A aplicação abre em `http://localhost:3000`. O passo a passo, as variáveis e os problemas conhecidos estão em [docs/onboarding.md](docs/onboarding.md); os checks, em [docs/quality.md](docs/quality.md).

## Documentação

| Assunto | Documento |
| --- | --- |
| Produto, público e escopo | [docs/project-overview.md](docs/project-overview.md) |
| Preparação local | [docs/onboarding.md](docs/onboarding.md) |
| Estrutura de pastas | [docs/project-structure.md](docs/project-structure.md) |
| Arquitetura e contratos | [openspec/specs/arquitetura-e-contratos.md](openspec/specs/arquitetura-e-contratos.md) |
| Modelo de domínio | [docs/domain-model.md](docs/domain-model.md) |
| Cliente HTTP, endpoints e deploy do Xano | [docs/xano-api-client.md](docs/xano-api-client.md) |
| Identidade e cargos | [docs/xano-auth-mapping.md](docs/xano-auth-mapping.md) |
| Design system e acessibilidade | [openspec/specs/design-system.md](openspec/specs/design-system.md) |
| Requisitos por área | [openspec/specs/](openspec/specs/) |
| Qualidade e checks | [docs/quality.md](docs/quality.md) |
| Instruções para agentes | [AGENTS.md](AGENTS.md) (importado por [CLAUDE.md](CLAUDE.md)) |
| Setup das ferramentas de IA e evidências | [docs/setup.md](docs/setup.md) |
