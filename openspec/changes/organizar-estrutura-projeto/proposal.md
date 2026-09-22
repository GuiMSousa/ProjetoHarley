# Proposta: organizar a estrutura do projeto

## Problema

O projeto mistura o código da aplicação com exports de uma integração externa, sem uma explicação única da função de cada pasta. Isso dificulta acompanhar o passo a passo do desenvolvimento.

## Objetivo

Separar a integração Xano das áreas principais e documentar uma sequência simples para localizar, implementar e validar funcionalidades.

## Escopo

- Mover `xano/` para `integrations/xano/`.
- Criar uma documentação curta da árvore do projeto.
- Criar um guia inicial no `README.md`.

## Fora do escopo

- Alterar o código da aplicação Reflex.
- Alterar tabelas, APIs ou exports do Xano.
- Alterar o modelo de dados ou regras de negócio.