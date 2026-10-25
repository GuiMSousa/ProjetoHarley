# Design: cadastros básicos do sistema

## Estratégia de entrega

A Change será implementada como cinco fatias de cadastro sobre uma base compartilhada:

1. infraestrutura de DTOs, erros, paginação visual e componentes de formulário;
2. clientes;
3. motos de clientes;
4. produtos e fornecedores;
5. funcionários e revisão transversal de autorização.

A fatia de motos depende de clientes. As demais podem reutilizar a infraestrutura comum, mas cada uma deve permanecer testável isoladamente.

## Contratos de domínio

Os DTOs devem refletir os campos existentes nos schemas Xano:

- `Cliente`: `id`, `nome_cliente`, `cpf_cnpj`, `telefone`, `email`, `endereco`.
- `MotoCliente`: `id`, `id_cliente`, `modelo`, `placa`, `chassi`.
- `Produto`: `id`, `codigo` definido por decisão de contrato, `nome_produto`, `descricao`, `categoria`, `estoque_qtd`, `preco_venda`.
- `Fornecedor`: `id`, `nome_fornecedor`, `cnpj`, `contato`.
- `Funcionario`: `id`, `nome_funcionario`, `cargo`, `tipo`, `contato`.

Payloads de criação e atualização devem ser modelos separados. Campos de identificação, datas e saldo controlado pelo backend não devem ser editáveis sem contrato explícito.

## Cliente Xano e serviços

`XanoClient` continuará sendo a fronteira de transporte e autenticação. Cada recurso terá métodos nomeados para listar, obter, criar, atualizar e desativar quando o endpoint existir.

Os serviços devem:

- usar os modelos Pydantic definidos para o recurso;
- converter respostas para DTOs antes de entregá-las ao estado Reflex;
- preservar `XanoAuthenticationError`, `XanoPermissionError` e `XanoValidationError`;
- normalizar erros de unicidade para mensagens orientadas à entidade;
- não duplicar montagem de headers, URL ou tratamento de `401`/`403`.

## Estado Reflex

Cada cadastro terá um estado responsável por:

- coleção atual e item selecionado;
- texto de busca e paginação da apresentação;
- carregamento inicial e carregamento de mutação;
- abertura/fechamento do modal;
- formulário de criação/edição;
- erro de validação e erro de API;
- eventos de listar, abrir formulário, salvar e desativar.

A busca textual deve ser aplicada de modo consistente e não deve alterar a fonte de verdade retornada pelo Xano. A paginação client-side somente será usada se o endpoint não fornecer paginação server-side.

## Componentes e rotas previstas

Arquivos existentes a estender:

- `Projeto_HarleyStore/Projeto_HarleyStore.py`: rotas protegidas dos cadastros e composição das páginas.
- `Projeto_HarleyStore/components.py`: navegação contextual, tabelas, modais, estados vazios e feedback.
- `Projeto_HarleyStore/services/xano_client.py`: métodos dos cinco recursos.
- `Projeto_HarleyStore/auth.py`: propriedades de autorização somente se a matriz exigir novos predicados.

Arquivos novos previstos:

- `Projeto_HarleyStore/services/clientes.py`
- `Projeto_HarleyStore/services/motos_clientes.py`
- `Projeto_HarleyStore/services/produtos.py`
- `Projeto_HarleyStore/services/fornecedores.py`
- `Projeto_HarleyStore/services/funcionarios.py`
- `Projeto_HarleyStore/states/clientes.py`
- `Projeto_HarleyStore/states/motos_clientes.py`
- `Projeto_HarleyStore/states/produtos.py`
- `Projeto_HarleyStore/states/fornecedores.py`
- `Projeto_HarleyStore/states/funcionarios.py`
- `Projeto_HarleyStore/pages/cadastros.py` ou módulos equivalentes conforme a organização existente
- componentes reutilizáveis de tabela, busca e modal, se a duplicação justificar a abstração

Testes novos previstos:

- `tests/test_clientes.py`
- `tests/test_motos_clientes.py`
- `tests/test_produtos.py`
- `tests/test_fornecedores.py`
- `tests/test_funcionarios.py`
- testes de serviços/DTOs e estados Reflex conforme o padrão estabelecido em `tests/`.

Arquivos Xano potencialmente alterados:

- schemas de `xano/table/produtos.xs` e endpoints correspondentes para `codigo` e eventual `ativo`;
- endpoints de `xano/api/harley/motos_clientes/` para alinhar vendedor e gerente;
- endpoints dos cinco recursos somente se o contrato atual não suportar os payloads ou ações aprovados.

## Matriz de UI e backend

A UI pode ocultar ações não permitidas para ergonomia, mas cada mutação deve ser rejeitada no Xano para perfis indevidos. `GERENTE` e `admin` superior devem manter acesso total conforme a Change 2.1.

Para `motos_clientes`, o contrato deve aceitar vendedor e mecânico somente conforme a decisão final da Change. Nesta proposta, a regra aprovada é vendedor com escrita e mecânico somente leitura; qualquer necessidade de mecânico editar deverá ser uma decisão explícita posterior.

## Plano de testes

- DTOs rejeitam preço inválido, estoque negativo, tipo de funcionário inválido e identificadores obrigatórios ausentes.
- Serviços enviam payloads corretos e interpretam respostas Xano tipadas.
- `401` limpa sessão; `403` preserva sessão e informa falta de permissão.
- Clientes rejeitam CPF/CNPJ duplicado e permitem busca e edição.
- Motos rejeitam placa/chassi duplicados e não permitem vínculo com cliente inexistente.
- Produtos rejeitam preço menor ou igual a zero e saldo negativo.
- Fornecedores rejeitam CNPJ duplicado.
- Funcionários aceitam somente os três tipos de domínio.
- Estados exibem loading, lista vazia, erro, sucesso e fechamento de modal.
- Testes de autorização cobrem gerente, vendedor e mecânico em cada recurso.
- `python -m py_compile`, suíte automatizada, `reflex compile --dry` e validação XanoScript serão executados antes do Archive.
