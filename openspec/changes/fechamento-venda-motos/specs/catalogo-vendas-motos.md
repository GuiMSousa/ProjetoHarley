# Delta de especificação: catálogo e vendas de motos

Alterações à spec `openspec/specs/catalogo-vendas-motos.md`, a aplicar no arquivamento.

## MODIFICADO — Requisito: matriz de acesso

| Operação | Visitante | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- | --- |
| Vitrine `/catalogo` | sim | sim | sim | sim |
| `/vendas`, unidades e histórico | não | sim | sim | não |
| Reservar | não | sim | sim | não |
| Cancelar reserva | não | qualquer | própria ou vencida | não |
| Vender | não | sim | sim | não |
| Gerir modelos e unidades | não | sim | não | não |

A frase "A conclusão da venda (`VENDIDA`) está fora deste requisito e será especificada na Change 9." DEVE ser removida.

## ADICIONADO — Requisito: fechamento da venda

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

## ADICIONADO — Requisito: placa opcional em motos de clientes

`motos_clientes.placa` DEVE aceitar nulo e DEVE continuar única quando informada. Placa em branco DEVE valer como ausente.

## ADICIONADO — Requisito: tela de fechamento

Em `/vendas`, `VENDEDOR` e `GERENTE` DEVEM ver a ação "Vender" nas unidades `DISPONIVEL` e `RESERVADA` com chassi. O formulário DEVE exigir cliente (fixo no cliente da reserva quando reservada) e valor maior que zero com até duas casas decimais, e DEVE aceitar placa opcional no padrão antigo ou Mercosul. Depois de uma venda aceita, a lista DEVE ser recarregada e o cache da vitrine invalidado.

### Cenário: unidade vendida por outro funcionário

- **DADO** o modal de venda aberto para uma unidade
- **QUANDO** outro funcionário concluir a venda dela antes e o Xano recusar a confirmação
- **ENTÃO** a lista DEVE ser recarregada mostrando a unidade como `VENDIDA`, o modal DEVE fechar e a mensagem do Xano DEVE ser exibida
