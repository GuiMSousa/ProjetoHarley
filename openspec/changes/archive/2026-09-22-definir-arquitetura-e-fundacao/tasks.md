# Tarefas

- [x] Atualizar a documentação arquitetural para declarar Xano como backend oficial e Reflex como frontend.
- [x] Padronizar os caminhos e referências do pacote `Projeto_HarleyStore`.
- [x] Documentar `xano/` como fonte versionada dos contratos do backend.
- [x] Converter `requirements.txt` de UTF-16LE para UTF-8 preservando o conteúdo.
- [x] Definir a configuração de ambiente para a URL base do Xano sem versionar segredos.
- [x] Criar a abstração de cliente HTTP do Reflex com suporte a métodos, headers, erros e JWT.
- [x] Definir o armazenamento de sessão e o comportamento para respostas `401` e `403`.
- [x] Definir e implementar o vínculo entre `user` e `Funcionarios`.
- [x] Validar o mapeamento de `admin`/`member` para os cargos de domínio sem substituir autorização por convenção.
- [x] Executar compilação do Reflex e checagens de encoding/documentação.
- [x] Registrar decisões pendentes da autenticação antes de iniciar a Change seguinte.

## Decisões deferidas

- O login, logout, renovação/expiração e armazenamento concreto da sessão serão implementados na Change de autenticação.
- A autorização operacional será implementada no backend Xano e validará o cargo do funcionário vinculado; o frontend não será a fonte de autorização.
