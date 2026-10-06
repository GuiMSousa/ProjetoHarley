// Detalhe público de um modelo ativo do catálogo (Change 8, D3), na mesma projeção da vitrine.
query "catalogo/{modelo_id}" verb=GET {
  api_group = "HARLEY"

  input {
    int modelo_id filters=min:1
  }

  stack {
    function.run "Catalogo/vitrine" {
      input = {modelo_id: $input.modelo_id}
    } as $vitrine

    precondition (($vitrine|count) > 0) {
      error_type = "notfound"
      error = "Modelo não encontrado no catálogo."
    }
  }

  response = $vitrine|first
  guid = "TfuXFRLZU2mn6kaR4rY6jY5t6Kc"
}
