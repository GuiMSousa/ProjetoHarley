# Modelo de Domínio — HarleyDavidsonStore

Este documento especifica as entidades, atributos conceituais e relacionamentos que regem o sistema da concessionária e oficina.

---

## Entidades Principais

### Fornecedores
Representa as empresas parceiras que fornecem peças, produtos e motocicletas para reposição de estoque.
- **Atributos:** Identificador (`id_fornecedor`), Nome/Razão Social (`nome_fornecedor`), CNPJ (`cnpj`), Contato (`contato`), Ativo (`ativo`).
- **Regras:** O CNPJ deve ser único no sistema.
- **Ciclo de vida:** `ativo = false` representa soft delete; o registro não deve ser removido fisicamente.

> **Exclusão física:** em todos os cadastros (fornecedores, produtos, funcionários, clientes, motos de clientes), nas motos da loja e nas transações, `DELETE` responde `403` desde o saneamento pós-Change 7. A desativação é sempre lógica, e nenhum registro vinculado a OS, estoque, entradas ou transações pode ficar órfão.

### Produtos
Representa os itens físicos comercializados pela concessionária ou utilizados na oficina mecânica.
- **Atributos:** Identificador (`id_produto`), Código (`codigo`), Nome (`nome_produto`), Descrição (`descricao`), Categoria (`categoria`), Quantidade em Estoque (`estoque_qtd`), Preço de Venda (`preco_venda`), Ativo (`ativo`).
- **Regras:** O saldo em estoque deve ser maior ou igual a zero (`estoque_qtd >= 0`) e o preço de venda deve ser estritamente positivo (`preco_venda > 0`).
- **Regras:** `codigo` deve ser alfanumérico e único; desativação usa soft delete.
- **Saldo:** `estoque_qtd` é informado apenas na criação (saldo inicial de implantação). Depois disso, só muda por movimentações de estoque (`Estoque/movimentar_estoque`); `PUT`/`PATCH produtos/{id}` ignoram o campo e também `versao_estoque`, o contador de movimentações usado para serializar movimentações concorrentes.

### Funcionarios
Representa os colaboradores da concessionária/oficina.
- **Atributos:** Identificador (`id_funcionario`), Nome (`nome_funcionario`), Cargo (`cargo`), Tipo (`tipo`), Contato (`contato`), Ativo (`ativo`).
- **Regras:** O tipo deve ser obrigatoriamente um entre: `VENDEDOR`, `MECANICO` ou `GERENTE`.
- **Ciclo de vida:** Funcionários não são removidos fisicamente quando já possuem vínculos; usam soft delete.
- **Acesso:** desativar um funcionário (`ativo = false`) revoga o acesso do usuário vinculado: `enforce_role` nega toda operação de negócio e o Reflex recusa a sessão.

### Usuários (identidade técnica)
Representa a identidade de autenticação do Xano (`user`), separada do domínio.
- **Atributos:** Identificador (`id`), Nome (`name`), Email (`email`, único), Senha (hash), Papel técnico (`role`: `admin` ou `member`), Funcionário vinculado (`id_funcionario`).
- **Regras:** Cada usuário operacional está vinculado a exatamente um funcionário ativo, e cada funcionário possui no máximo um usuário. O cargo de domínio vem de `Funcionarios.tipo`; `role` é apenas técnico.
- **Criação:** somente um `GERENTE` cria usuários (`auth/signup`), com email e senha obrigatórios; o endpoint não emite token para o novo usuário.
- **Troca de senha:** `reset/update_password` altera apenas a senha do próprio usuário, exige a senha atual e um funcionário vinculado ativo, e rejeita a nova senha igual à atual.
- **Auditoria:** `event_log` registra login e criação de usuário com id, email, papel e vínculo; senhas, hashes e tokens nunca são gravados.

### Clientes
Representa os proprietários de motocicletas ou compradores da loja.
- **Atributos:** Identificador (`id_cliente`), Nome (`nome_cliente`), CPF/CNPJ (`cpf_cnpj`), Telefone (`telefone`), Email (`email`), Endereço (`endereco`), Ativo (`ativo`).
- **Regras:** CPF ou CNPJ deve ser único no sistema.
- **Ciclo de vida:** A desativação é lógica e preserva o histórico operacional.

### Motos_Clientes
Representa os veículos pertencentes a clientes e utilizados no fluxo da oficina para manutenção, revisão e histórico de serviços.
- **Atributos:** Identificador (`id_moto_cliente`), Cliente Vinculado (`id_cliente`), Modelo (`modelo`), Placa (`placa`), Chassi (`chassi`), Ativo (`ativo`).
- **Relacionamento:** Pertence a um **Cliente**.
- **Regras:** Placa e Chassi devem ser únicos no sistema.
- **Ciclo de vida:** A desativação é lógica e não remove o veículo do histórico.

### Motos
Representa as motocicletas mantidas no estoque da loja e destinadas à venda. Esta entidade é independente de `motos_clientes` e não representa o veículo usado no histórico de oficina.
- **Atributos:** Identificador (`id`), Cliente opcional (`clientes_id`), Marca (`marca`), Modelo (`modelo`), Data de Cadastro (`created_at`).
- **Relacionamento:** Pode possuir um cliente associado quando a venda for registrada.
- **Situação atual:** o schema ainda não possui preço, chassi, status de disponibilidade nem `ativo`. O `DELETE` físico está bloqueado (`403`) até que a Change de catálogo defina o ciclo de vida das motos da loja.

### Entrada_Mercadoria & Itens_Compra_Estoque
Representa a nota/registro de compra efetuada junto a um fornecedor para abastecimento de estoque.
- **Atributos Entrada:** Identificador (`id_entrada`), Fornecedor (`id_fornecedor`), Número do Documento (`numero_documento`), Funcionário Responsável (`id_funcionario`), Data da Entrada (`data_entrada`), Valor Total (`valor_total`).
- **Atributos Itens da Compra:** Identificador (`id_item_compra`), Entrada (`id_entrada`), Produto (`id_produto`), Quantidade (`quantidade`), Valor Unitário (`valor_unitario`, exibido como "preço de custo").
- **Relacionamentos:** Uma entrada possui um ou mais **Itens de Compra**, pertence a um **Fornecedor** e é registrada por um **Funcionário**.
- **Regras:** A quantidade deve ser estritamente positiva (`quantidade > 0`) e o valor unitário deve ser estritamente positivo (`valor_unitario > 0`).
- **Regras:** O fornecedor e todos os produtos devem existir e estar ativos; um mesmo produto não pode se repetir na entrada; `(id_fornecedor, numero_documento)` é único.
- **Regras financeiras:** `valor_total = Σ (quantidade × valor_unitario)`, calculado pelo Xano; valores enviados pelo cliente são ignorados.
- **Atomicidade:** cabeçalho, itens e incremento de `produtos.estoque_qtd` (movimentação `ENTRADA` no livro) são gravados em uma única `db.transaction` por `POST entrada_mercadoria`. Qualquer rejeição desfaz a operação inteira.
- **Autoria:** `id_funcionario` e `data_entrada` são definidos pelo servidor a partir do usuário autenticado.
- **Registros legados:** `numero_documento` e `id_funcionario` são anuláveis no schema para que entradas anteriores à Change 5 não colidam no índice único; a função `Estoque/normalizar_entradas_legadas` preenche documentos vazios com `LEGADO-<id>`.
- **Ciclo de vida:** Entradas e itens são imutáveis após o registro; os endpoints de edição e exclusão respondem `403`. Estornos serão tratados em Change futura com movimentação inversa.
- **Concorrência:** desde a Change 7, o incremento usa o livro de movimentações com versão por produto; entradas e baixas simultâneas do mesmo produto não se sobrescrevem (a segunda falha e é desfeita). Os itens são processados em ordem de `id_produto`, a mesma do cancelamento de OS, para evitar deadlock.

### Movimentacoes_Estoque
Livro de movimentações de estoque (kardex), somente inserção.
- **Atributos:** Identificador (`id`), Produto (`id_produto`), Tipo (`tipo`: `ENTRADA`, `SAIDA_OS` ou `ESTORNO_OS`), Quantidade (`quantidade`, sempre positiva), Saldo Anterior (`saldo_anterior`), Saldo Posterior (`saldo_posterior`), Versão Anterior (`versao_anterior`), Funcionário (`id_funcionario`), Origem (`id_entrada`, `id_os`, `id_item_os`), Data (`created_at`).
- **Regras:** toda alteração de saldo depois da criação do produto gera exatamente uma linha, gravada pela função `Estoque/movimentar_estoque` dentro da transação da operação de origem. `saldo_posterior >= 0`: uma saída acima do saldo é rejeitada ("Saldo insuficiente…").
- **Concorrência:** a função lê saldo e `produtos.versao_estoque` na mesma leitura, grava o livro com `versao_anterior` e o produto com a versão seguinte. O índice único `(id_produto, versao_anterior)` impede que duas movimentações concorrentes partam da mesma versão.
- **Invariante:** para produtos movimentados a partir da Change 7, `estoque_qtd` é igual ao `saldo_posterior` da última movimentação.

### Ordens_Servico & Itens_Ordem_Servico
Representa o atendimento técnico prestado na oficina mecânica para a moto de um cliente.
- **Atributos OS:** Identificador (`id_os`), Moto do Cliente (`id_moto_cliente`), Cliente (`id_cliente`), Autor da abertura (`id_funcionario`), Mecânico Responsável (`id_mecanico`), Tipo de Serviço (`tipo_servico`: `PREVENTIVA` ou `CORRETIVA`), Descrição do Problema (`descricao_problema`), Quilometragem (`quilometragem`), Data de Abertura (`data_abertura`), Data de Início (`data_inicio`), Data de Encerramento (`data_encerramento`), Motivo do Cancelamento (`motivo_cancelamento`), Status (`status`).
- **Atributos OS (valores):** Total de Peças (`valor_pecas`), Total de Mão de Obra (`valor_servicos`), Total Geral (`valor_total`) e Última Mutação (`atualizado_em`).
- **Atributos Itens OS:** Identificador (`id_item_os`), Ordem de Serviço (`id_os`), Tipo (`tipo_item`: `PECA` ou `SERVICO`), Produto (`id_produto`, somente peças), Descrição (`descricao`, somente serviços), Quantidade (`quantidade`), Valor Unitário (`valor_unitario`), Valor Total do Item (`valor_total_item`), Estoque Baixado (`estoque_baixado`), Funcionário que incluiu (`id_funcionario`), Data (`created_at`).
- **Relacionamentos:** Pertence a uma **Moto_Cliente** e ao **Cliente** dono da moto na abertura; é aberta por um **Funcionario** (autor) e executada por um **Funcionario** do tipo `MECANICO`; é composta por vários **Produtos/Peças**.
- **Abertura:** a OS nasce sempre `ABERTA`, com `data_abertura` do servidor. A moto e o cliente devem estar ativos; o mecânico responsável deve ser um funcionário ativo do tipo `MECANICO` (quando o autor é mecânico e não informa outro, ele próprio é o responsável). `tipo_servico` e `descricao_problema` são obrigatórios; `quilometragem`, opcional e `>= 0`.
- **Cliente:** `id_cliente` é uma fotografia do dono da moto no momento da abertura e preserva o histórico se a moto mudar de dono.
- **Uma OS em aberto por moto:** não é possível abrir uma OS para uma moto que já tenha outra `ABERTA` ou `EM_ANDAMENTO`.
- **Máquina de estados:** `ABERTA → EM_ANDAMENTO | CANCELADA`; `EM_ANDAMENTO → CONCLUIDA | CANCELADA`. `CONCLUIDA` e `CANCELADA` são finais; não há reabertura nem `ABERTA → CONCLUIDA`. O cancelamento exige motivo. As transições ocorrem somente por `POST ordens_servico/{id}/status`, que preenche `data_inicio` ao iniciar e `data_encerramento` ao concluir ou cancelar.
- **Histórico de status (`historico_status_os`):** cada abertura e cada transição grava status anterior, novo status, funcionário autenticado, data e observação. O índice único `(id_os, status_anterior)` garante que cada OS saia de cada status uma única vez e serializa transições concorrentes.
- **Controle otimista:** a transição informa o status visto pelo usuário (`status_atual`); se a OS tiver mudado, a operação é rejeitada sem efeito.
- **Autoria:** `id_funcionario` e o funcionário do histórico vêm do usuário autenticado (`$auth.id → user.id_funcionario`), nunca do payload. Edição e exclusão diretas de OS (`PUT`/`PATCH`/`DELETE`) respondem `403`.
- **Itens:** incluídos e removidos somente por `POST`/`DELETE ordens_servico/{id}/itens`, por `GERENTE` ou `MECANICO`, em OS `ABERTA` ou `EM_ANDAMENTO`; OS `CONCLUIDA` e `CANCELADA` têm itens congelados. Não há edição de item: para mudar a quantidade, remove-se e inclui-se de novo. As rotas genéricas de `itens_ordem_servico` respondem `403`.
- **Peças:** o preço é a fotografia de `produtos.preco_venda` na inclusão; a peça sai do estoque no momento da inclusão (`SAIDA_OS`), com verificação de saldo. Um mesmo produto aparece uma única vez na OS.
- **Serviços (mão de obra):** descrição e valor unitário informados por quem inclui; não movimentam estoque.
- **Devolução:** remover uma peça baixada ou cancelar a OS devolve as peças ao estoque (`ESTORNO_OS`) na mesma transação. Concluir a OS não movimenta estoque. A OS cancelada mantém itens e totais como registro do orçamento.
- **Valores:** `valor_total_item = quantidade × valor_unitario` e os totais da OS são calculados pelo Xano a partir dos itens; valores enviados pelo cliente são ignorados. `quantidade` e `valor_total_item` devem ser positivos.
- **Concorrência dos itens:** inclusão, remoção e transição começam atualizando `atualizado_em` da OS, o que trava a linha e as serializa; assim, uma peça incluída durante o cancelamento é devolvida por ele ou a inclusão é rejeitada.
- **Registros legados:** os campos das Changes 6 e 7 são anuláveis; OS anteriores continuam legíveis e podem seguir a máquina de estados a partir do status gravado. Itens anteriores à Change 7 são lidos como peças sem baixa (`estoque_baixado` nulo): podem ser removidos, sem devolução ao estoque.

### Transacoes
Registra o fluxo financeiro de vendas e movimentações comerciais do estabelecimento.
- **Atributos:** Identificador (`id_transacao`), Tipo da Transação (`tipo_transacao`), Funcionário (`id_funcionario`), Cliente (`id_cliente`), Moto do Cliente (`id_moto_cliente`), Data (`data_transacao`), Valor Total (`valor_total`).
- **Regras:** O tipo de transação deve ser restrito aos valores: `MOTO`, `PECAS`, `BALCAO`, `COMPRA`, `ORDEM_SERVICO`.
- **Regras financeiras:** `valor_total` deve ser estritamente positivo (`> 0`).
- **Autoria:** `id_funcionario` deve ser derivado do usuário autenticado e do vínculo `user.id_funcionario`. `POST`/`PUT` gravam o funcionário do JWT e o `PATCH` descarta `id_funcionario` do payload.
- **Situação atual:** transações não possuem linhas de itens; vendas de peças com baixa de estoque dependem de uma decisão de modelagem ainda pendente. O `DELETE` físico está bloqueado (`403`); `PUT`/`PATCH` ainda são genéricos e serão revistos na Change de vendas.

---

## Visão Consolidada (`vw_resumo_operacoes`)
O domínio conta com um consolidado conceitual de operações que unifica as **Transações Comerciais** e as **Entradas de Mercadorias** para relatórios e consultas gerais de fluxo operacional.