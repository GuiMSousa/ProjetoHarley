# Proposta: fotos das motos vindas do Xano (Change 17)

## Contexto e objetivo

Change pedida diretamente para execução (2026-10-27). As fotos das motos vinham de duas fontes: a foto principal do Xano (`imagem_principal`, URL https) e uma galeria local por modelo em `assets/motos/<slug>/`. A galeria local só existia para os quatro modelos originais, e `/vendas` dependia só dela, porque `GET motos` não devolvia a foto do modelo. Um modelo novo, como o "Breakout", ficava sem galeria. Na vitrine, a página tentava abrir um `default_<slug>.png` que não existia (404).

O objetivo é que toda foto venha do Xano: a principal (`imagem_principal`) e as do carrossel (`galeria`). Sem foto, a tela mostra uma imagem neutra própria (SVG embutido), nunca um arquivo por pasta.

Estado verificado em 2026-10-27:
- os 5 modelos publicados têm `imagem_principal` em `www.harley-davidson.com`, e as 5 URLs respondem 200 com JPEG;
- as fotos das cores são placeholders (`placehold.co`);
- a coluna `galeria` (`image[1:10]?`) existe no Xano publicado, criada pelo painel, mas não estava em `xano/` nem era devolvida pelos endpoints.

## Escopo

- **Xano (push com `-i` e OK do usuário):**
  - `xano/table/modelos_moto.xs` passa a versionar `galeria` e `default_motos` exatamente como estão publicadas. Não há mudança de banco; só evita que um push apague as colunas.
  - `Catalogo/vitrine` devolve `galeria` como a lista dos `path` das imagens (`/vault/...`).
  - `Vendas/detalhe_moto` devolve a `galeria` do modelo da unidade; `GET motos` devolve a `imagem_principal` do modelo.
- **Reflex:**
  - DTOs de leitura transformam cada item da `galeria` (um `path` `/vault/...`, um objeto com `path` ou uma URL http(s)) em URL absoluta. O `path` ganha a origem de `XANO_API_BASE_URL`, e qualquer outro valor é descartado.
  - `MotoEstoque` ganha `imagem_principal` e `galeria`.
  - `get_foto_moto` e `get_lista_fotos_moto` usam só o Xano: foto da cor, foto principal, `galeria`, e por fim a imagem neutra.
  - A leitura de foto de cor passa a aceitar só http(s), porque os caminhos locais deixam de existir.
- **Remoção:** `assets/motos/` (16 fotos e 4 artes padrão) e a cópia gerada em `.web/public/motos/`.

## Decisões

- **D1 — `path` em vez de objeto na resposta:** o objeto de imagem do Xano não tem `url`, só `path`. Num arquivo público, a URL é a origem da instância mais o `path`. A vitrine devolve só o `path` (a projeção pública não expõe nome nem metadados do arquivo), e o Reflex monta a URL com a origem que já conhece. A instância não é versionada.
- **D2 — Só fotos públicas:** um arquivo privado precisaria de URL assinada. As fotos da galeria DEVEM ser enviadas como públicas.
- **D3 — Placeholder embutido:** um SVG em `data:`, gerado com as cores do tema, sem arquivo e sem chamada externa.
- **D4 — `default_motos` versionada sem uso:** a decisão de manter ou remover continua no item 5 da Change 16.

## Fora do escopo

- Envio de fotos pelo app (upload no `/vendas`). As fotos da galeria são enviadas pelo painel do Xano.
- Trocar as fotos de cor (`placehold.co`) por fotos reais: é dado, não código.

## Riscos

- Até o push e o envio das fotos, o carrossel mostra só a foto principal de cada modelo. As fotos removidas continuam no histórico do Git (`git checkout 9e41407 -- assets/motos`) para o envio pelo painel.
- Uma URL externa fora do ar aparece como imagem quebrada; o app não verifica a URL.

## Status

Apply em 2026-10-27; push pendente do OK do usuário.
