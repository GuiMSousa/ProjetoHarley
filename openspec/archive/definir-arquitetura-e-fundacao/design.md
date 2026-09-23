# Design: definir-arquitetura-e-fundacao

## Decisões

### Backend e fonte de verdade

O Xano é o backend oficial. Os arquivos em `xano/` representam schemas, APIs e funções versionadas do backend. O Reflex não acessa tabelas diretamente e não usa `docs/schema.sql` em runtime.

O SQL Server documentado anteriormente fica somente como referência histórica até ser removido ou substituído por documentação equivalente do Xano.

### Organização do frontend

O pacote da aplicação é `Projeto_HarleyStore/`, conforme `rxconfig.py`. O Reflex concentra componentes, estado, páginas e o cliente de integração HTTP.

O cliente HTTP deve ser uma abstração única da aplicação, responsável por:

- montar a URL base a partir de configuração de ambiente;
- enviar `Authorization: Bearer <JWT>` quando houver sessão;
- tratar respostas não autorizadas sem duplicar lógica nas páginas;
- diferenciar erros de transporte, autenticação e validação da API;
- não registrar tokens, senhas ou respostas sensíveis em logs.

A URL base e outros valores de ambiente não devem ser embutidos no código ou commitados como segredos.

### Contrato de autenticação

O endpoint Xano de login retorna um `authToken` e um `user_id`. O cliente Reflex deve manter o token apenas no mecanismo de armazenamento de sessão escolhido para a aplicação, com expiração coerente com o JWT. O token não deve ser colocado em query string, URL ou estado público renderizado.

Chamadas autenticadas devem enviar o JWT no cabeçalho `Authorization`. Respostas `401` devem limpar a sessão local e encaminhar o usuário para a autenticação. O tratamento de `403` deve preservar a sessão e informar falta de permissão.

A implementação concreta do armazenamento e do fluxo de login pertence à Change de autenticação.

### Mapeamento de identidade

A tabela Xano `user` é a identidade técnica e possui os papéis técnicos `admin` e `member`. A entidade de domínio `Funcionarios` representa a pessoa colaboradora e possui `tipo` com os valores `GERENTE`, `VENDEDOR` e `MECANICO`.

O vínculo deverá ser explícito, preferencialmente por um campo de referência `id_funcionario` na tabela `user`, ou por uma tabela de associação caso o Xano exija preservação do schema atual. Não será feita inferência por nome ou e-mail.

A autorização de negócio deve consultar o funcionário vinculado e validar o cargo de domínio. O papel técnico Xano não substitui o cargo de funcionário:

| Identidade Xano | Domínio | Uso inicial |
| --- | --- | --- |
| `admin` | funcionário com `tipo = GERENTE` | administração e operações gerenciais |
| `member` | funcionário com `tipo = VENDEDOR` ou `MECANICO` | operações permitidas pelo cargo |

Essa tabela é um mapeamento inicial de compatibilidade, não uma autorização completa. A próxima Change deve definir permissões por operação e impedir usuários sem funcionário vinculado de acessar o domínio operacional.

### Codificação

`requirements.txt` será convertido de UTF-16LE para UTF-8 sem alterar conteúdo ou versões. Arquivos de código e documentação novos devem permanecer em UTF-8.

## Fluxo de dependências

```text
Configuração de ambiente
        |
        v
Cliente HTTP Reflex ----> JWT Xano
        |                    |
        v                    v
Estado de sessão       user + Funcionarios
        |
        v
Páginas e APIs de negócio
```

## Consequências

- A aplicação fica desacoplada da persistência interna do Xano.
- Contratos de API passam a ser a fronteira entre Reflex e backend.
- O vínculo entre usuário autenticado e funcionário precisa ser criado antes de autorizar operações de negócio.
- A Change de autenticação deverá definir detalhes ainda não implementados: endpoint final, expiração, renovação, logout e política de permissões.
