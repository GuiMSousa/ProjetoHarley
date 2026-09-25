// Preenche numero_documento vazio de entradas legadas com "LEGADO-<id>".
// Idempotente: executar uma vez após publicar o schema da Change 5, antes de
// depender do índice único (id_fornecedor, numero_documento).
function "Estoque/normalizar_entradas_legadas" {
  input {
  }

  stack {
    db.query entrada_mercadoria {
      where = $db.entrada_mercadoria.numero_documento == null || $db.entrada_mercadoria.numero_documento == ""
      return = {type: "list"}
    } as $legadas

    foreach ($legadas) {
      each as $entrada {
        db.edit entrada_mercadoria {
          field_name = "id"
          field_value = $entrada.id
          data = {
            numero_documento: "LEGADO-" ~ $entrada.id
          }
        } as $normalizada
      }
    }
  }

  response = {normalizadas: $legadas|count}
  guid = "u29UQsgDQkzH6PqdBKoRM70ha6M"
}
