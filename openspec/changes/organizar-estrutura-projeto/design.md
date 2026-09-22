# Design: organização da estrutura

## Decisão

Manter as pastas de execução do Reflex na raiz do projeto e agrupar arquivos de sistemas externos em `integrations/`. O diretório `LOJAHARLEY/` permanece com esse nome porque corresponde ao `app_name` definido em `rxconfig.py`.

## Resultado

- O Reflex continua encontrando `rxconfig.py` e o pacote `LOJAHARLEY/` no mesmo nível.
- Os 218 exports Xano ficam isolados em `integrations/xano/`.
- A documentação passa a indicar a ordem de leitura e os destinos de novos arquivos.