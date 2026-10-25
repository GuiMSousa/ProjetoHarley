# Proposta: design system Harley-Davidson e catálogo e reservas de motos

## Contexto

As Changes 1 a 7 e o saneamento pós-Change 7 entregaram autenticação, cadastros, entrada de mercadoria com livro de estoque, oficina com máquina de estados e itens, e o fechamento dos débitos de segurança prioritários. A auditoria (`docs/auditoria-arquitetura-changes-1-7.md`) considerou a arquitetura pronta para o redesign visual e pronta com condições para o catálogo de motos.

Estado atual:

- **Visual:**
  - `styles/theme.py` tem uma paleta escura provisória (`#070707`, `#f36f21`, `#a7a7a7`) e fonte Arial;
  - o acento do Radix é o `orange` padrão, que não é o laranja da marca;
  - os títulos não seguem um padrão e cada página monta seus próprios cabeçalhos, tabelas e badges;
  - o `status_badge` vive em `workshop_pages.py`;
  - o dashboard é um texto provisório com cor fixa, os cadastros mostram o preço cru (`45.9`) e o shell não tem estado ativo nem adaptação a telas pequenas.
- **Motos da loja:**
  - a tabela `motos` tem apenas `clientes_id`, `marca` e `modelo`; não tem família, preço, imagens, chassi nem status;
  - `POST`/`PATCH motos` são genéricos (`dblink`), `GET motos` devolve o registro cru a todos os perfis e `DELETE` está bloqueado desde o saneamento;
  - no cliente, `list_motos`, `create_moto` e `update_moto` não têm tela nem testes.
- **Superfície pública:** somente `auth/login` é público (spec `arquitetura-e-contratos`).
- **Limite de requisições:** o workspace do Xano responde `429` depois de cerca de 6 chamadas seguidas, e o `XanoClient` trata esse código como falha genérica.

## Problema

1. A interface não transmite a identidade da marca e acumula variações visuais que o redesign precisa unificar antes de novas telas surgirem.
2. A concessionária não consegue expor nem vender as motos do estoque. Não há vitrine, preço, disponibilidade nem reserva, e o schema de `motos` não distingue o modelo comercial (família, cores, preço de vitrine) da unidade física (chassi, cor, status).
3. Uma vitrine pública chamaria o Xano a cada visita, a partir do mesmo backend Reflex, e esbarraria no limite de `429`.

## Objetivo

Entregar em três fases, cada uma com verificação própria:

- **Fase A — design system:** tokens e componentes centralizados e aplicação uniforme em Login, Dashboard, Cadastros, Entradas e Oficina.
- **Fase B — catálogo:** modelos de moto com família, preço "a partir de", imagem principal e variações de cor; vitrine `/catalogo` estilo showroom (hero, abas por família, busca, cards com seletor de cores e detalhe).
- **Fase C — reservas:** unidades em estoque com chassi e status; tela interna `/vendas` para reservar uma unidade disponível para um cliente e cancelar reservas, e gestão do catálogo pelo gerente.

A conclusão da venda (`VENDIDA` com transação financeira `MOTO`) fica para a Change 9, junto com o redesenho de `transacoes` apontado pela auditoria.

## Decisões de negócio

- **Modelo × unidade (D2):**
  - `modelos_moto` é o catálogo comercial: nome, família, descrição, preço base, imagem principal, variações de cor e destaque;
  - `motos` passa a ser a unidade física: modelo, chassi, cor, ano, preço de venda e status;
  - "A partir de R$ X" é o menor preço entre as unidades disponíveis do modelo; sem unidades disponíveis, vale o preço base, e o card mostra "Sob consulta".
- **Status da unidade:** `DISPONIVEL → RESERVADA → DISPONIVEL` (cancelamento) e, na Change 9, `RESERVADA | DISPONIVEL → VENDIDA`, que será estado final.
  - O status só muda pelos endpoints de reserva;
  - cadastro e edição nunca aceitam status nem cliente.
- **Reserva (D5):**
  - `VENDEDOR` ou `GERENTE` reserva uma unidade `DISPONIVEL` para um cliente ativo, com validade de 1 a 30 dias (padrão 7) e observação opcional;
  - quem reservou ou um `GERENTE` pode cancelar, informando o motivo;
  - uma reserva vencida pode ser cancelada por qualquer vendedor;
  - não há expiração automática nesta Change.
- **Vitrine pública (D3):**
  - a listagem e o detalhe do catálogo podem ser consultados sem login, apenas com campos de vitrine (nunca cliente, vendedor, chassi ou histórico) e apenas de modelos ativos;
  - reservar exige login.
- **Imagens (D4):** URLs `https://` informadas pelo gerente, sem upload nesta Change. A loja deve usar imagens próprias ou licenciadas, nunca copiadas ou hospedadas no site oficial da Harley-Davidson.
- **Identidade visual (D9, D10):**
  - paleta preto asfalto `#000000`, preto fosco `#121212`, cinza industrial `#1A1A1A`, laranja Harley `#FF6600`, branco `#FFFFFF` e cinza metálico `#A0A0A0`;
  - títulos em caixa alta com fonte condensada de licença livre;
  - não usar o logotipo nem as fontes proprietárias da marca, e sim uma assinatura textual ("HARLEY STORE");
  - o texto sobre o laranja é sempre preto.

## Escopo

### Fase A — design system (Reflex)

- **Tokens (`styles/theme.py`):**
  - cores com as chaves atuais remapeadas para a nova paleta;
  - tipografia (títulos em Oswald, corpo em Inter), espaçamentos, raios, sombras;
  - estilos de botão (primário laranja, metálico, perigo), card, tabela e mapa único de cores de status (OS e motos).
- **Folha global `assets/harley.css`:**
  - sobrescreve o acento do Radix para `#FF6600`;
  - aplica caixa alta e espaçamento de letras a todos os `rx.heading`;
  - define o anel de foco laranja e o fundo preto.
- **Componentes em `ui_helpers.py`:**
  - `page_header`, `section_title`, `card`, `primary_button`, `metal_button`, `danger_button`;
  - `status_badge` único (OS e motos), `data_table`, `empty_state`, `stat_tile`;
  - além dos atuais `labeled` e `error_callout`.
- **Componentes em `components.py`:**
  - shell com sidebar em seções (Operação, Oficina, Vendas, Cadastros), item ativo destacado e recolhível em telas menores que 768 px;
  - login redesenhado;
  - `modal_panel` com backdrop em blur;
  - `public_shell` para páginas sem login.
- **Aplicação em todas as telas:**
  - Login;
  - Dashboard: atalhos por perfil, sem métricas;
  - Cadastros, com o preço formatado por `format_currency`;
  - Entradas;
  - Oficina: `workshop_pages.py` dividido em lista e detalhe.

### Fase B — catálogo (Xano, Python, Reflex)

- **Xano:**
  - tabela nova `modelos_moto`;
  - `GET catalogo` (filtros `familia` e `busca`) e `GET catalogo/{modelo_id}` públicos com projeção de vitrine;
  - `GET`/`POST modelos_moto` e `PATCH modelos_moto/{id}` para `GERENTE`, com inputs explícitos e validação de URL `https://` e de cor hexadecimal.
- **Python:**
  - `services/catalogo.py` com `FamiliaMoto`, `VariacaoCor`, `ModeloMotoCreate`/`Update`, `ModeloMoto` e `ModeloCatalogo`;
  - métodos `list_catalogo`, `get_modelo_catalogo`, `list_modelos_moto`, `criar_modelo_moto` e `atualizar_modelo_moto`;
  - `XanoRateLimitError` para `429`, com a mensagem "Muitas requisições, aguarde alguns segundos";
  - cache em memória do catálogo público (TTL de 60 s), invalidado nas escritas do gerente.
- **Reflex:**
  - `/catalogo` público: hero com o modelo em destaque, abas Todas | Touring | Cruiser | Adventure | Sport, busca por modelo e grade responsiva de cards;
  - cada card tem foto, modelo em caixa alta, família, "A partir de R$ X", disponibilidade e swatches de cor que trocam a foto;
  - modal de detalhe com galeria por cor;
  - o botão "Tenho interesse" leva ao login (visitante) ou a `/vendas` filtrado pelo modelo (vendedor e gerente).

### Fase C — estoque e reservas (Xano, Python, Reflex)

- **Xano:**
  - evolução de `motos`: `id_modelo`, `chassi` (normalizado e único), `cor`, `ano_modelo`, `preco_venda`, `status`, `id_vendedor_reserva`, `reservada_ate`, `versao_status` e `atualizado_em`;
  - tabela nova `historico_status_moto`, com índice único `(id_moto, versao_anterior)`;
  - função central `Vendas/transicionar_moto` e `Vendas/detalhe_moto`;
  - `GET motos` e `GET motos/{id}` (`VENDEDOR`, enriquecidos);
  - `POST motos` e `PATCH motos/{id}` (`GERENTE`, inputs explícitos, sem status nem cliente);
  - `PUT motos/{id}` bloqueado;
  - `POST motos/{id}/reserva` e `POST motos/{id}/reserva/cancelar` (`VENDEDOR`).
- **Python:**
  - `services/motos.py` reescrito com `StatusMoto`, `MotoEstoqueCreate`/`Update`, `MotoEstoque`, `MotoEstoqueDetalhe`, `ReservaMotoCreate`, `CancelamentoReservaMoto` e `HistoricoStatusMoto`;
  - métodos `list_motos_estoque`, `get_moto_estoque`, `cadastrar_moto_estoque`, `atualizar_moto_estoque`, `reservar_moto` e `cancelar_reserva_moto`;
  - remoção de `Moto`, `MotoCreate`, `MotoUpdate`, `list_motos`, `create_moto` e `update_moto`.
- **Reflex `/vendas` (`VENDEDOR`, `GERENTE`):**
  - abas Disponíveis, Reservadas e Vendidas (esta só leitura, vazia até a Change 9);
  - filtros por modelo e família, e busca por chassi, modelo ou cliente;
  - modal de reserva (cliente, validade, observação) e cancelamento com motivo;
  - linha do tempo da unidade;
  - aba Estoque (`GERENTE`): gerir modelos (com editor de variações de cor e pré-visualização dos swatches) e unidades.

### Testes e documentação

- Testes de tokens (incluindo a razão de contraste WCAG dos pares de cor usados), componentes, DTOs, cliente HTTP, regras puras e eventos dos estados, e contratos XanoScript.
- Integração: catálogo sem token, ciclo de reserva e cancelamento, e reserva concorrente.
- Verificação visual das telas em 1440 px e 390 px.
- No Archive, atualizar `docs/domain-model.md`, `docs/xano-api-client.md`, `openspec/specs/arquitetura-e-contratos.md` e criar `openspec/specs/catalogo-vendas-motos.md` e `openspec/specs/design-system.md`.

## Matriz de acesso

| Operação | Visitante | GERENTE | VENDEDOR | MECANICO |
| --- | --- | --- | --- | --- |
| Ver catálogo e detalhe de modelo (`/catalogo`) | sim | sim | sim | sim |
| Ver unidades em estoque, reservas e histórico (`/vendas`) | não | sim | sim | não |
| Reservar unidade disponível | não | sim | sim | não |
| Cancelar reserva | não | sim (qualquer) | própria ou vencida | não |
| Criar e editar modelos e unidades | não | sim | não | não |
| Concluir venda (`VENDIDA`) | — | Change 9 | Change 9 | — |

## Fora do escopo

- Conclusão da venda, transação `MOTO`, criação da moto do cliente em `motos_clientes` e redesenho de `transacoes` (Change 9).
- Expiração automática de reservas (tarefa agendada no Xano).
- Upload de imagens para o armazenamento do Xano.
- Formulário público de interesse ou captação de leads (LGPD).
- Métricas no dashboard.
- Tela de troca de senha.
- Modo claro.
- Ficha técnica estruturada por modelo (cilindrada, peso e similares): nesta Change há apenas a descrição livre.
- Os demais débitos da auditoria (normalização de placa e CPF/CNPJ, `try_catch` na entrada, `user.id_funcionario` único e outros), exceto os absorvidos pelo redesign (D11) e o `429` (D12).

## Critérios de aceite

- **Design system:**
  - todas as telas existentes usam os tokens e componentes do design system;
  - não restam cores hexadecimais fora de `styles/theme.py` e `assets/harley.css` (verificado por teste);
  - os títulos aparecem em caixa alta, e o acento do Radix (foco, abas, seleção) é `#FF6600`.
- **Contraste:** todo par de texto e fundo definido nos tokens atinge 4,5:1; texto sobre laranja é sempre preto.
- **Status:** OS e motos usam o mesmo `status_badge`, com cores fixas por status.
- **Catálogo:**
  - `/catalogo` abre sem login e mostra hero, abas por família, busca e cards;
  - clicar num swatch troca a foto do card sem nova chamada ao Xano;
  - o preço aparece como "A partir de R$ 189.900,00";
  - o detalhe mostra a galeria por cor e a disponibilidade.
- **Limite de requisições:** recarregar `/catalogo` várias vezes seguidas não gera novas chamadas ao Xano dentro do TTL do cache; um `429` mostra a mensagem de espera, nunca "falha de comunicação".
- **Endpoints públicos:** `GET catalogo` e `GET catalogo/{id}` respondem sem token, sem `clientes_id`, chassi, vendedor ou histórico, e somente com modelos ativos.
- **Escritas:**
  - `POST`/`PATCH motos` ignoram `status`, cliente e vendedor enviados;
  - `PUT` e `DELETE motos/{id}` respondem `403`;
  - chassi duplicado, inclusive contra `motos_clientes`, é rejeitado com `400`;
  - URL que não comece com `https://` e cor fora de `#RRGGBB` são rejeitadas.
- **Reserva:**
  - só unidade `DISPONIVEL` é reservada, para cliente ativo;
  - a unidade passa a `RESERVADA` com cliente, vendedor do JWT e validade do servidor;
  - uma linha de histórico é gravada por transição.
- **Concorrência:** duas reservas simultâneas da mesma unidade resultam em exatamente uma aceita.
- **Cancelamento:** por outro vendedor, antes do vencimento, é rejeitado com `403`; pelo gerente, ou depois do vencimento, é aceito; o motivo é obrigatório.
- **Perfis:**
  - `MECANICO` e visitante não acessam `/vendas`;
  - chamadas forjadas de reserva, cancelamento ou gestão recebem `401`/`403`.
- **Verificação antes do Archive:** suíte automatizada, `py_compile`, `reflex compile --dry`, validador XanoScript e revisão visual das telas.

## Dependências

- Saneamento pós-Change 7 publicado no Xano.
- Imagens próprias ou licenciadas, hospedadas em `https://`, para ao menos um modelo por família nos testes.
- Credenciais de teste por perfil para a integração, e tratamento do `429` antes de rodar a integração completa.

## Decisões para validação

- **D1 — Uma Change em três fases:** A (design system), B (catálogo) e C (estoque e reservas), cada uma com verificação própria antes da seguinte; a venda (`VENDIDA` com transação) vai para a Change 9. A alternativa é separar em Changes 8, 9 e 10, com mais cerimônia e menos risco por entrega. *Recomendado.*
- **D2 — Modelo comercial separado da unidade física:** `modelos_moto` (catálogo) e `motos` (unidade com chassi e status). A alternativa, uma tabela única como no pedido literal, deixa sem sentido as variações de cor e o "a partir de" numa unidade que tem uma só cor e um só preço. *Recomendado.*
- **D3 — Vitrine pública:**
  - `GET catalogo` e `GET catalogo/{id}` sem autenticação, com projeção fechada, e `/catalogo` fora do login;
  - exige emendar o requisito "superfície pública mínima";
  - a alternativa é um catálogo interno, só com login, que mantém o requisito como está. *Confirmar.*
- **D4 — Imagens por URL `https://`:** sem upload, com validação no Xano e responsabilidade da loja pelos direitos das imagens. *Recomendado.*
- **D5 — Regras da reserva:** validade de 1 a 30 dias (padrão 7), cancelamento por quem reservou, pelo gerente ou por qualquer vendedor após o vencimento, e sem expiração automática. *Confirmar.*
- **D6 — Concorrência por versão:** `motos.versao_status` com índice único `(id_moto, versao_anterior)` em `historico_status_moto`, o padrão do livro de estoque da Change 7. O padrão `(id, status_anterior)` da Change 6 não serve, porque `DISPONIVEL ↔ RESERVADA` tem ciclos. *Recomendado.*
- **D7 — Status só pelos endpoints de reserva:** `POST`/`PATCH motos` com inputs explícitos (sem `dblink`), sem status nem cliente; `PUT` bloqueado. *Recomendado.*
- **D8 — Gestão do catálogo na interface:** aba Estoque em `/vendas` para o gerente criar e editar modelos (com editor de cores) e unidades; sem ela, o módulo dependeria do painel do Xano. *Recomendado.*
- **D9 — Tema e tipografia:**
  - acento do Radix sobrescrito por variáveis CSS em `assets/harley.css`;
  - Oswald nos títulos e Inter no corpo, via Google Fonts (licença OFL);
  - caixa alta por CSS (`text-transform`), preservando o texto original para leitores de tela;
  - sem logotipo nem fonte proprietária. *Recomendado.*
- **D10 — Contraste:** texto sobre `#FF6600` sempre preto (7,15:1; branco dá 2,94:1 e reprova no WCAG AA); `#A0A0A0` só para texto secundário (6,66:1 sobre `#1A1A1A`); os pares são garantidos por teste. *Recomendado.*
- **D11 — Débitos de UI absorvidos:** `status_badge` único, divisão de `workshop_pages.py`, preço formatado nos cadastros e fim da cor fixa no dashboard. O `workshop_state.py` não é dividido, porque é uma única classe de estado coberta por testes. *Recomendado.*
- **D12 — `429` e cache:** `XanoRateLimitError` com mensagem própria e cache de 60 s do catálogo público no backend Reflex, com filtros de família e busca aplicados localmente sobre a lista em cache. *Recomendado.*
- **D13 — Dashboard com atalhos por perfil:** cards para as áreas permitidas, sem métricas (que exigiriam novas chamadas ao Xano). *Recomendado.*
- **D14 — Rotas:** `/catalogo` público com link na sidebar para todos; `/vendas` para `GERENTE` e `VENDEDOR`; `GET motos` deixa de ser `ALL` e passa a `VENDEDOR`. *Recomendado.*

## Resultado aplicado

Decisões D1 a D13 aprovadas integralmente. A D14 (matriz de rotas) foi aplicada conforme a proposta, já que a aprovação cobriu a proposta inteira e pediu a atualização do `ROUTE_ROLES`. As três fases foram aplicadas e verificadas em sequência.

- **Fase A — design system:**
  - tokens remapeados em `styles/theme.py` (paleta, fontes, gradientes, botões, `STATUS_COLORS`, `TEXT_PAIRS`, `contrast_ratio`) e `assets/harley.css` (acento `#FF6600`, Oswald e Inter, títulos em caixa alta, foco laranja);
  - componentes novos em `ui_helpers.py`: `page_header`, `section_title`, `card`, os três botões, `modal_header`, `toolbar`, `pager`, `data_table`, `empty_state`, `stat_tile`, `status_badge` único e `swatch`;
  - shell novo em `components.py`: sidebar em seções com item ativo, gaveta abaixo de 768 px, `public_shell`, login redesenhado, `modal_panel` com blur e `page_body`;
  - telas redesenhadas: login, dashboard (`dashboard_pages.py`, atalhos por perfil), cadastros (preço formatado e badge de situação), entradas e oficina, esta dividida em `workshop_pages.py` e `workshop_detail.py`.
- **Fase B — catálogo:**
  - tabela `modelos_moto`, função `Catalogo/vitrine`, `GET catalogo` e `GET catalogo/{id}` públicos, e `GET`/`POST`/`PATCH modelos_moto` para o gerente;
  - `services/catalogo.py`, com DTOs e o cache `TtlCache` de 60 s;
  - `XanoRateLimitError` para o `429`;
  - página `/catalogo`: hero, abas por família, busca local, cards com swatches e detalhe.
- **Fase C — estoque e reservas:**
  - `motos` evoluída e tabela `historico_status_moto`;
  - funções `Vendas/transicionar_moto` e `Vendas/detalhe_moto`;
  - endpoints de unidades reescritos, `PUT` bloqueado, reserva e cancelamento;
  - função `Catalogo/seed_exemplo`, com dados de exemplo;
  - `services/motos.py` reescrito e métodos novos no `XanoClient` (os antigos `list_motos`, `create_moto` e `update_moto` foram removidos);
  - página `/vendas`: abas por status, filtro `?modelo=`, reserva, cancelamento, linha do tempo e aba Estoque do gerente, com editor de cores.
- **Testes:** a suíte passou de 209 para 264 testes.

### Notas de implementação

- **Dados de exemplo:** a população de exemplo não pôde ser gravada a partir do repositório, porque a publicação e a execução no Xano são feitas pelo usuário. Foi entregue a função idempotente `Catalogo/seed_exemplo` (um modelo por família, cores e unidades), a ser executada uma vez no Xano. As imagens são placeholders neutros de `placehold.co`, a trocar por fotos próprias ou licenciadas (D4).
- **Chamada à ação da vitrine:**
  - para o visitante, "Fale com um vendedor" abre o detalhe com a orientação de procurar a loja (o design previa levar a `/login`, que é o acesso dos funcionários);
  - para vendedor e gerente, "Reservar" leva a `/vendas?modelo={id}`;
  - o perfil é lido de `AuthState.allowed_routes`, e não de uma variável computada do `CatalogoState`. Essa variável criava uma dependência entre estados que quebrava o fixture dos testes de autenticação.
- **Detalhe da vitrine:** a página usa os cards já em cache em vez de chamar `GET catalogo/{id}`, para poupar requisições (`429`). O endpoint fica disponível para outros consumidores.
- **Busca no Xano:** a busca por nome é aplicada na lista com `icontains`, depois da consulta, que é a alternativa prevista no design.
- **Gramática do XanoScript:**
  - `object[]` não aceita `filters`, por isso o limite de 12 cores é uma `precondition`;
  - os argumentos de `pattern:` e `startsWith:` precisam de aspas;
  - `ok:#…` não é aceito.
- **Reflex 0.9.12:**
  - `router.page` está depreciado, e a sidebar e a leitura de `?modelo=` usam `router.url`;
  - `rx.segmented_control` e `foreach` aninhado com dataclasses funcionam;
  - `is_loading` já existe no `AuthState`, e o catálogo usa `is_loading_catalogo`.
- **Reuso:**
  - `normalize_text` foi para `listing.py` (oficina e catálogo);
  - `validation_feedback` foi para `feedback.py` (oficina e vendas);
  - o `status_badge` também cobre `ATIVO`/`INATIVO` dos cadastros.
- **Verificação visual:**
  - o app subiu em modo produção e os screenshots foram feitos com o Edge headless;
  - login e `/catalogo` foram conferidos a 1440 px e a 390 px, este com iframes, porque o Edge desktop tem largura mínima de cerca de 500 px;
  - a revisão encontrou e corrigiu no catálogo móvel: abas que transbordavam, cabeçalho que quebrava (o botão virou "Entrar" no celular) e o estado "Nenhum modelo" exibido antes do fim do carregamento (novo `carregado`);
  - as telas internas e os cards com dados não foram revistos visualmente: exigem credenciais e a Change publicada, e a vitrine mostra "Catálogo indisponível no momento" até o push.
- **Build de produção:** exibe o selo "Built with Reflex", padrão do Reflex.

## Status

Aplicada, verificada e arquivada em 2026-09-29.

- `python -m unittest discover -s tests`: 264 testes, com 232 executados e aprovados e 32 de integração ignorados, por falta de credenciais, das flags de escrita e concorrência, ou porque o catálogo ainda não foi publicado.
- `python -m py_compile`: 51 módulos, OK.
- `reflex compile --dry`: OK.
- Validador XanoScript: 121 arquivos, 0 erros.
- Revisão visual (Edge headless, produção): login e `/catalogo` a 1440 px e 390 px.

Pendente fora do repositório:

- `xano workspace push -d ./xano` (aditivo);
- executar `Catalogo/seed_exemplo` com o id de um gerente e trocar os placeholders por imagens próprias;
- rodar a integração com `XANO_TEST_*`, `XANO_TEST_ALLOW_WRITES=true` e `XANO_TEST_CONCURRENCY=true`;
- revisar visualmente as telas internas com um usuário real.
