# Especificação: catálogo, reservas e vendas de motos

## Requisito: modelo comercial separado da unidade

O catálogo (`modelos_moto`) DEVE descrever o modelo comercial: nome único, família (`TOURING`, `CRUISER`, `ADVENTURE`, `SPORT`), descrição, preço base, imagem principal, até 12 variações de cor (`nome`, `#RRGGBB`, foto `https://`), destaque e ativo. Cada unidade física (`motos`) DEVE referenciar um modelo e ter chassi, cor, ano, preço de venda e status próprios.

### Cenário: validação de imagens e cores

- **DADO** um gerente cadastrando um modelo
- **QUANDO** informar uma imagem `http://` ou uma cor fora de `#RRGGBB`
- **ENTÃO** o cadastro DEVE ser rejeitado com `400`

## Requisito: vitrine pública

`GET catalogo` (filtros opcionais `familia` e `busca`) e `GET catalogo/{id}` DEVEM responder sem autenticação, apenas com modelos ativos e apenas com os campos `id`, `nome_modelo`, `familia`, `descricao`, `imagem_principal`, `galeria`, `variacoes_cor`, `destaque`, `preco_a_partir` e `disponiveis`. `galeria` (Change 17) DEVE trazer só o `path` de cada imagem pública do modelo, nunca o objeto do arquivo. `preco_a_partir` DEVE ser o menor preço entre as unidades `DISPONIVEL` do modelo ou, sem unidades, o preço base.

### Cenário: modelo sem unidades

- **DADO** um modelo ativo sem unidades disponíveis e preço base 79.900,00
- **QUANDO** um visitante abrir `/catalogo`
- **ENTÃO** o card DEVE mostrar "A partir de R$ 79.900,00" e "Sob consulta"

### Cenário: dados internos

- **DADO** uma unidade reservada para um cliente
- **QUANDO** o catálogo público for consultado
- **ENTÃO** a resposta NÃO DEVE conter chassi, cliente, vendedor nem histórico

## Requisito: vitrine resistente ao limite de requisições

A página `/catalogo` DEVE reutilizar a lista do catálogo por 60 segundos entre sessões e aplicar família e busca localmente; escritas do gerente DEVEM invalidar o cache. Uma resposta `429` DEVE exibir uma mensagem de espera, nunca "falha de comunicação".

### Cenário: troca de cor

- **DADO** um card com várias cores
- **QUANDO** o visitante clicar num swatch
- **ENTÃO** a foto do card DEVE trocar para a foto daquela cor sem nova chamada ao Xano

## Requisito: cadastro de unidades

Somente o `GERENTE` DEVE cadastrar e editar unidades, com inputs explícitos. O chassi DEVE ser um VIN de 17 caracteres, normalizado em caixa alta e único em `motos` e em `motos_clientes`; a cor DEVE ser uma das variações do modelo; o ano DEVE estar entre 1990 e o ano seguinte. A unidade DEVE nascer `DISPONIVEL`, com uma linha de histórico. Cadastro e edição NÃO DEVEM aceitar status, cliente, vendedor nem validade; `PUT` e `DELETE motos/{id}` DEVEM responder `403`.

## Requisito: reserva

`VENDEDOR` ou `GERENTE` DEVE poder reservar uma unidade `DISPONIVEL` (com modelo) para um cliente ativo, com validade de 1 a 30 dias (padrão 7). O vendedor DEVE vir do JWT e a validade DEVE ser calculada pelo servidor. Cada transição DEVE gravar uma linha em `historico_status_moto`.

### Cenário: reservas simultâneas

- **DADO** uma unidade `DISPONIVEL`
- **QUANDO** dois vendedores a reservarem ao mesmo tempo
- **ENTÃO** exatamente uma reserva DEVE ser aceita e a outra DEVE receber `400`

## Requisito: cancelamento da reserva

O cancelamento DEVE exigir motivo e só DEVE ser aceito para quem reservou, para um `GERENTE` ou, depois do vencimento, para qualquer vendedor. A unidade DEVE voltar a `DISPONIVEL`, sem cliente, vendedor ou validade.

### Cenário: outro vendedor antes do vencimento

- **DADO** uma reserva válida do vendedor A
- **QUANDO** o vendedor B tentar cancelá-la
- **ENTÃO** a resposta DEVE ser `403`

## Requisito: fechamento da venda

`POST vender_moto` DEVE aceitar somente `id_moto`, `id_cliente`, `valor_venda` (mínimo 0,01), `placa` (opcional) e `observacao` (opcional, até 500 caracteres); o funcionário DEVE vir do JWT. Uma venda aceita DEVE, numa única transação, criar a moto do cliente em `motos_clientes` (com o nome do modelo comercial e o chassi da unidade), registrar uma transação `MOTO` com `valor_total = valor_venda` e passar a unidade a `VENDIDA`, com uma linha em `historico_status_moto`. A resposta DEVE ser `{id_transacao, id_moto_cliente, status: "SUCESSO"}`. `VENDIDA` DEVE ser estado final.

### Cenário: venda de unidade disponível sem placa

- **DADO** uma unidade `DISPONIVEL` com chassi e um cliente ativo
- **QUANDO** um vendedor a vender por R$ 185.000,00 sem informar placa
- **ENTÃO** a unidade DEVE ficar `VENDIDA` com o cliente, DEVE existir uma transação `MOTO` de 185.000,00 e uma moto do cliente sem placa

### Cenário: unidade reservada para outro cliente

- **DADO** uma unidade `RESERVADA` para o cliente A
- **QUANDO** um vendedor tentar vendê-la ao cliente B
- **ENTÃO** a resposta DEVE ser `400` "Esta moto está reservada para outro cliente." e nada DEVE ser gravado

### Cenário: venda repetida

- **DADO** uma unidade `VENDIDA`
- **QUANDO** alguém tentar vendê-la de novo
- **ENTÃO** a resposta DEVE ser `400` "Esta moto já foi vendida."

### Cenário: vendas simultâneas

- **DADO** uma unidade `DISPONIVEL`
- **QUANDO** dois vendedores a venderem ao mesmo tempo
- **ENTÃO** exatamente uma venda DEVE ser aceita, a outra DEVE receber `400` e DEVE existir uma única moto do cliente e uma única transação para a unidade

### Cenário: placa duplicada

- **DADO** uma moto de cliente com placa `ABC1D23`
- **QUANDO** uma venda informar a placa `abc1d23`
- **ENTÃO** a resposta DEVE ser `400` "Placa já cadastrada em uma moto de cliente."

## Requisito: placa opcional em motos de clientes

`motos_clientes.placa` DEVE aceitar nulo e DEVE continuar única quando informada. Placa em branco DEVE valer como ausente.

## Requisito: tela de fechamento

Em `/vendas`, `VENDEDOR` e `GERENTE` DEVEM ver a ação "Vender" nas unidades `DISPONIVEL` e `RESERVADA` com chassi. O formulário DEVE exigir cliente (fixo no cliente da reserva quando reservada) e valor maior que zero com até duas casas decimais, e DEVE aceitar placa opcional no padrão antigo ou Mercosul. Depois de uma venda aceita, a lista DEVE ser recarregada e o cache da vitrine invalidado.

### Cenário: unidade vendida por outro funcionário

- **DADO** o modal de venda aberto para uma unidade
- **QUANDO** outro funcionário concluir a venda dela antes e o Xano recusar a confirmação
- **ENTÃO** a lista DEVE ser recarregada mostrando a unidade como `VENDIDA`, o modal DEVE fechar e a mensagem do Xano DEVE ser exibida

## Requisito: matriz de acesso

| Operação | Visitante | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- | --- |
| Vitrine `/catalogo` | sim | sim | sim | sim |
| `/vendas`, unidades e histórico | não | sim | sim | não |
| Reservar | não | sim | sim | não |
| Cancelar reserva | não | qualquer | própria ou vencida | não |
| Vender | não | sim | sim | não |
| Gerir modelos e unidades | não | sim | não | não |
