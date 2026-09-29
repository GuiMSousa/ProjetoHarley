// Catálogo comercial das motos da loja (Change 8): família, preço base, imagens e cores.
// A unidade física (chassi, cor, preço e status) fica em motos.
table modelos_moto {
  auth = false

  schema {
    int id
    text nome_modelo filters=trim
    enum familia {
      values = ["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
    }

    text? descricao? filters=trim

    // Preço de vitrine usado quando não há unidade disponível.
    decimal preco_base filters=min:0.01

    // URL https validada no endpoint; imagens próprias ou licenciadas pela loja.
    text imagem_principal filters=trim

    // [{nome, hex, imagem_url}] com até 12 cores, validada no endpoint.
    json? variacoes_cor?

    // Candidato ao hero da vitrine.
    bool? destaque?=false

    // Soft delete: modelos inativos saem do catálogo.
    bool? ativo?=true

    timestamp created_at?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "nome_modelo"}]}
    {type: "btree", field: [{name: "familia"}]}
  ]
}
