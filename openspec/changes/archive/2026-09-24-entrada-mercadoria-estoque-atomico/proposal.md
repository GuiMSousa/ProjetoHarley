# Proposta: entrada de mercadoria, movimentação atômica de estoque e ajustes de consistência

## Contexto

As Changes 1 a 4 entregaram a fundação Xano/Reflex, a autenticação por JWT com cargo de funcionário, os cinco cadastros básicos e o hardening de autoria e valores financeiros. Os produtos já possuem `estoque_qtd >= 0`, mas nenhuma operação de negócio movimenta esse saldo.

O backend possui as tabelas `entrada_mercadoria` e `itens_compra_estoque` e endpoints CRUD gerados para ambas, porém:

- `POST entrada_mercadoria` grava somente o cabeçalho (`id_fornecedor`, `data_entrada`, `valor_total`), sem itens e sem atualizar estoque;
- `valor_total` é informado pelo cliente, e não calculado a partir dos itens;
- `itens_compra_estoque` pode ser criado, editado e removido isoladamente, sem qualquer reflexo em `produtos.estoque_qtd`;
- a entrada não registra o funcionário responsável nem o número do documento fiscal;
- não há validação de fornecedor ativo nem de produto ativo;
- `GET entrada_mercadoria` e `GET itens_compra_estoque` exigem `VENDEDOR`, o que bloqueia o `MECANICO`, contrariando a matriz desejada para consulta.

No frontend, não existe tela de entrada de mercadorias. Também foram identificadas inconsistências de sessão e navegação:

- as rotas `/cadastros/*` não restauram a sessão no `on_load` nem verificam autenticação antes de renderizar o App Shell; após F5, `employee_role` fica vazio e as ações por perfil desaparecem;
- falhas de carregamento das listas são gravadas em `error_message`, que não é exibido nas telas de cadastro;
- o link "Produtos e peças" da sidebar aparece apenas para `GERENTE` e `MECANICO`, embora o `VENDEDOR` tenha leitura de produtos.

## Problema

A loja não consegue registrar a chegada de mercadorias de forma confiável. Qualquer composição manual (cabeçalho + itens + ajuste de estoque em chamadas separadas) pode deixar estoque, itens e totais divergentes quando uma das etapas falha, quando o usuário repete o envio ou quando um endpoint de item é chamado diretamente. A ausência de autoria e de número de documento também impede a auditoria da compra.

## Objetivo

Entregar a primeira movimentação de estoque do sistema: registrar uma entrada de mercadoria com seus itens em uma única operação atômica no Xano, que incrementa `produtos.estoque_qtd`, calcula o total no servidor e registra o funcionário autenticado como responsável. No Reflex, disponibilizar o histórico e o formulário mestre-detalhe dentro do App Shell, e corrigir as inconsistências de sessão e navegação encontradas nas rotas de cadastro.

## Decisões de negócio

- A entrada de mercadoria é registrada por um único endpoint que recebe cabeçalho e itens juntos; não existe entrada sem itens.
- O incremento de estoque, a gravação dos itens e o cálculo do `valor_total` ocorrem no Xano, dentro de uma transação de banco. Se qualquer validação falhar, nada é persistido.
- `valor_total = Σ (quantidade × valor_unitario)` é calculado exclusivamente pelo servidor; valores de total enviados pelo cliente são ignorados.
- O "preço de custo" da interface corresponde ao campo persistido `itens_compra_estoque.valor_unitario`.
- O responsável (`id_funcionario`) é derivado de `$auth.id → user.id_funcionario`, seguindo o padrão da Change 4.
- Entradas registradas são imutáveis nesta Change. Correções e estornos serão tratados em Change futura com movimentação inversa de estoque.
- O saldo de estoque passa a ser alterado somente por movimentações. A edição manual de `estoque_qtd` em produtos existentes deixa de ser permitida (ver decisão D3).
- O Xano continua sendo a autoridade final; o frontend reflete permissões e valida antes do envio.

## Escopo

### Xano

- Evoluir o schema de `entrada_mercadoria`:
  - `numero_documento` (texto, obrigatório, `trim`);
  - `id_funcionario` (referência a `funcionarios`, preenchido pelo stack);
  - índice único composto `(id_fornecedor, numero_documento)`.
- Reescrever `POST entrada_mercadoria` para receber `{id_fornecedor, numero_documento, itens: [{id_produto, quantidade, valor_unitario}]}` e executar, dentro de `db.transaction`:
  1. autorização `GERENTE` via `Quick Start/enforce_role`;
  2. resolução do funcionário autenticado;
  3. validação de fornecedor existente e ativo;
  4. validação de lista de itens não vazia e sem produtos repetidos;
  5. validação de cada produto existente e ativo, `quantidade >= 1` e `valor_unitario >= 0.01`;
  6. criação do cabeçalho, dos itens e incremento de `estoque_qtd` de cada produto;
  7. gravação do `valor_total` calculado.
- Ajustar `GET entrada_mercadoria` para retornar a lista enriquecida com nome do fornecedor, nome do responsável e quantidade de itens, e liberar a leitura para `ALL` (`GERENTE`, `VENDEDOR`, `MECANICO`).
- Ajustar `GET entrada_mercadoria/{id}` para retornar o cabeçalho enriquecido e os itens com `codigo` e `nome_produto`, com leitura para `ALL`.
- Bloquear as mutações diretas que contornam o estoque: `PUT`, `PATCH` e `DELETE` de `entrada_mercadoria/{id}`, e `POST`, `PUT`, `PATCH` e `DELETE` de `itens_compra_estoque`.
- Ajustar `GET itens_compra_estoque` e `GET itens_compra_estoque/{id}` para leitura `ALL`.
- Impedir a alteração de `estoque_qtd` por `PATCH`/`PUT produtos/{id}`.
- Validar todos os XanoScript alterados.

### Python (DTOs e cliente)

- Criar `Projeto_HarleyStore/services/entradas.py` com DTOs Pydantic:
  - `ItemEntradaCreate` (`id_produto > 0`, `quantidade > 0`, `valor_unitario: Decimal > 0`);
  - `EntradaMercadoriaCreate` (`id_fornecedor > 0`, `numero_documento` não vazio, `itens` com pelo menos um item e sem produto repetido);
  - `EntradaMercadoriaResumo` (leitura do histórico);
  - `ItemEntrada` e `EntradaMercadoriaDetalhe` (leitura do detalhamento).
- Adicionar ao `XanoClient` os métodos `list_entradas`, `get_entrada` e `registrar_entrada`. Não haverá métodos de edição ou exclusão de entradas.
- Mapear `400` do Xano (`inputerror` de `precondition`) para `XanoValidationError`, expondo a mensagem de negócio de forma segura para validações (`400`/`422`).
- Remover `estoque_qtd` de `ProdutoUpdate` e do formulário de edição de produtos, mantendo-o apenas na criação (saldo inicial de implantação).

### Reflex

- Criar a rota `/estoque/entradas` com:
  - histórico de entradas com busca textual, paginação client-side, estados de carregamento, vazio e erro;
  - modal de detalhamento dos itens de uma entrada;
  - formulário mestre-detalhe, somente para `GERENTE`, com seleção de fornecedor ativo, número do documento, adição e remoção dinâmica de itens (produto ativo, quantidade e preço de custo) e prévia do total;
  - bloqueio de envio duplicado e feedback por toast para sucesso, validação, `401`, `403` e falha de transporte.
- Adicionar o link "Entradas de mercadoria" à sidebar para os três perfis.
- Criar um guard reutilizável de página autenticada e aplicá-lo às rotas `/cadastros/*` e `/estoque/entradas`, restaurando a sessão no `on_load` antes de carregar os dados.
- Tornar `role_allows_route` a fonte única da matriz de rotas no frontend, cobrindo `/admin`, `/workshop`, `/cadastros/*` e `/estoque/entradas`.
- Exibir o link "Produtos e peças" também para `VENDEDOR`, em modo somente leitura.
- Exibir nas telas de cadastro o erro de carregamento da lista, hoje silencioso.
- Extrair a lógica compartilhada de busca e paginação para evitar duplicação entre cadastros e entradas.

### Testes e documentação

- Testes de DTO, cliente HTTP, estado Reflex, guards e contratos XanoScript (detalhados em `tasks.md`).
- Atualizar `docs/domain-model.md` e `docs/xano-api-client.md`.
- Consolidar os requisitos aprovados em `openspec/specs/` no Archive.

## Matriz de acesso

| Recurso | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- |
| Entradas de mercadoria (histórico e detalhe) | leitura | leitura | leitura |
| Registrar entrada de mercadoria | sim | não | não |
| Editar ou excluir entrada registrada | não (imutável) | não | não |
| Produtos e saldo de estoque | CRUD (saldo só por movimentação) | leitura | leitura |
| Rotas `/cadastros/clientes` e `/cadastros/motos-clientes` | escrita | escrita | leitura |
| Rota `/cadastros/produtos` | escrita | leitura | leitura |
| Rotas `/cadastros/fornecedores` e `/cadastros/funcionarios` | escrita | sem acesso | sem acesso |

O gerente técnico `admin` validamente vinculado mantém acesso superior no backend, conforme `enforce_role`.

## Fora do escopo

- Estorno, cancelamento ou edição de entrada já registrada.
- Baixa de estoque por venda de balcão, venda de peças ou itens de OS.
- Criação automática de registro em `transacoes` do tipo `COMPRA` (ver decisão D6).
- Custo médio, histórico de preço de custo ou atualização de `preco_venda` a partir da compra.
- Paginação server-side e filtros por período.
- Ordens de serviço, vendas e dashboard.
- Entrada de motocicletas de estoque (`motos`).
- Integração fiscal (NF-e, XML, chave de acesso).
- Novo framework frontend ou acesso direto do Reflex ao banco.

## Critérios de aceite

- Um gerente registra uma entrada com N itens e cada produto tem `estoque_qtd` incrementado exatamente pela quantidade informada.
- `valor_total` persistido é igual a `Σ (quantidade × valor_unitario)`, independentemente de qualquer total enviado no payload.
- Uma entrada com qualquer item inválido (quantidade `<= 0`, preço `<= 0`, produto inexistente ou inativo, produto repetido) é rejeitada sem gravar cabeçalho, itens ou alteração de estoque.
- Uma entrada com fornecedor inexistente ou inativo é rejeitada sem efeitos colaterais.
- Uma entrada sem itens é rejeitada.
- Um segundo envio com o mesmo `(id_fornecedor, numero_documento)` é rejeitado e não duplica estoque.
- `id_funcionario` persistido é sempre o do usuário autenticado, mesmo que o payload contenha outro valor.
- Vendedor e mecânico consultam o histórico e o detalhe, mas recebem `403` ao tentar registrar; a interface não exibe a ação para eles.
- Chamadas diretas a `PUT/PATCH/DELETE entrada_mercadoria/{id}` e às mutações de `itens_compra_estoque` são rejeitadas.
- `PATCH/PUT produtos/{id}` não altera `estoque_qtd`.
- Após F5 em qualquer rota `/cadastros/*` ou `/estoque/entradas`, a sessão é restaurada e as ações por perfil reaparecem; sem token, o usuário vê a tela de login.
- Acesso direto de vendedor ou mecânico a `/cadastros/fornecedores` ou `/cadastros/funcionarios` exibe acesso negado.
- O vendedor vê "Produtos e peças" na sidebar e não vê ações de escrita na tela.
- Mensagens de rejeição de negócio vindas do Xano aparecem de forma legível, sem expor token ou payload bruto.
- Suíte automatizada, `py_compile`, `reflex compile --dry` e validação XanoScript executados antes do Archive.

## Dependências

- Changes 1 a 4 arquivadas.
- Suporte a `db.transaction` no XanoScript do workspace, com rollback em `precondition`/`throw` (confirmar na documentação Xano durante o Apply).
- Fornecedores e produtos ativos cadastrados para teste.
- Usuários de teste para os três perfis.
- Instância Xano com `XANO_API_BASE_URL` para comprovar atomicidade e rollback; sem ela, a verificação fica restrita a testes de contrato estático e à validação sintática.

## Decisões para validação

- **D1 — Unicidade do documento:** `numero_documento` único por fornecedor (índice `(id_fornecedor, numero_documento)`). Também serve como proteção contra envio duplicado. *Recomendado.*
- **D2 — Imutabilidade:** bloquear os endpoints de mutação direta de entradas e itens, mantendo os arquivos com resposta de rejeição explícita em vez de removê-los do export. *Recomendado.*
- **D3 — Saldo só por movimentação:** remover `estoque_qtd` da edição de produtos (Reflex e Xano), mantendo o saldo inicial na criação. Altera o comportamento entregue na Change 3. *Recomendado.*
- **D4 — Concorrência:** o incremento será leitura e escrita dentro de `db.transaction`. Duas entradas simultâneas do mesmo produto podem, em teoria, sofrer atualização perdida conforme o nível de isolamento do Xano. Alternativa: `db.direct_query` com `UPDATE ... SET estoque_qtd = estoque_qtd + ?`, se o plano Xano permitir. *Recomendado aceitar a primeira opção nesta Change e registrar o risco, dado o volume baixo de entradas simultâneas.*
- **D5 — Data da entrada:** `data_entrada` definida pelo servidor (`now`), sem data informada pelo usuário. *Recomendado.*
- **D6 — Transação financeira `COMPRA`:** não criar registro em `transacoes` nesta Change. *Recomendado.*
- **D7 — Leitura de fornecedores:** `GET fornecedores` está hoje como `ALL` no Xano, divergindo da matriz da Change 3 (sem acesso para vendedor e mecânico). Como o histórico de entradas passará a trazer o nome do fornecedor enriquecido pelo servidor, é possível restringir `GET fornecedores` a `GERENTE`. *Recomendado incluir o alinhamento nesta Change.*

## Resultado aplicado

Decisões D1 a D7 aprovadas integralmente.

- `entrada_mercadoria` recebeu `numero_documento`, `id_funcionario`, índice único `(id_fornecedor, numero_documento)` e índice por data.
- `POST entrada_mercadoria` passou a receber cabeçalho e itens e a gravar tudo em `db.transaction`: valida fornecedor e produtos ativos, documento único, itens não vazios e sem repetição, incrementa `estoque_qtd`, calcula `valor_total` e deriva o responsável do JWT.
- Nova função `Estoque/detalhe_entrada`, reutilizada pelo `POST` e pelo `GET entrada_mercadoria/{id}`.
- Leituras de entradas e itens abertas a `ALL`, com nomes de fornecedor, responsável e produtos enriquecidos no servidor.
- Sete endpoints de mutação direta de entradas e itens passaram a responder `403` (D2).
- `PUT`/`PATCH produtos/{id}` deixaram de alterar `estoque_qtd` (D3); `GET fornecedores` restrito a `GERENTE` (D7).
- DTOs em `services/entradas.py`, métodos `list_entradas`, `get_entrada` e `registrar_entrada`, e `400` mapeado para `XanoValidationError` com mensagem de negócio segura.
- Rota `/estoque/entradas` com histórico, busca, paginação, modal de detalhe e formulário mestre-detalhe restrito ao gerente.
- Matriz `ROUTE_ROLES` única, guard `guarded_page`, restauração de sessão no `on_load` de todas as rotas protegidas, sidebar corrigida para o vendedor, erro de carregamento visível nos cadastros e toast vazio removido de `load_user`.
- Busca, paginação e opções de select extraídas para `listing.py` e reutilizadas por cadastros e entradas.
- A suíte passou de 26 para 74 testes automatizados.

### Notas de implementação

- A documentação XanoScript mostra `isolation` em `db.transaction`, mas o validador oficial (`@xano/developer-mcp` 2.2.6) rejeita a propriedade. Por isso o incremento segue a D4 sem nível de isolamento explícito, com o risco de concorrência documentado.
- O total é calculado antes do `db.add` do cabeçalho, que já grava o valor final. Não foi necessário um valor provisório.
- `quantidade_itens` do histórico é obtida por uma contagem por entrada (N+1 consultas). É adequado ao volume atual e deve ser revisto junto com a paginação server-side.
- `Decimal` continua serializado como string JSON, seguindo a convenção já usada por `ProdutoCreate`.
- O teste da Change 2.1 que proibia qualquer texto do corpo em erros `422` foi dividido: `401`, `403` e `5xx` continuam sem expor o corpo, e `400`/`422` expõem somente `message` textual curta, conforme o design aprovado.

## Status

Aplicada, verificada e arquivada em 2026-09-24.

Verificação:

- `python -m unittest discover -s tests`: 74 testes, todos OK.
- `python -m py_compile` nos arquivos Python da aplicação e dos testes: OK.
- `reflex compile --dry`: OK.
- Validação XanoScript com `@xano/developer-mcp`: 99 arquivos, 0 erros.

A integração contra uma instância Xano real, incluindo a prova de rollback, não foi executada porque não há `XANO_API_BASE_URL` nem credenciais configuradas neste workspace. A atomicidade está coberta por testes de contrato estático e pela validação sintática.
