// Vitrine pública do catálogo de motos (Change 8, D3): sem autenticação, somente campos
// de vitrine de modelos ativos. Filtros opcionais por família e busca pelo nome do modelo.
query catalogo verb=GET {
  api_group = "HARLEY"

  input {
    enum? familia? {
      values = ["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
    }

    text? busca? filters=trim|max:80
  }

  stack {
    function.run "Catalogo/vitrine" {
      input = {familia: $input.familia, busca: $input.busca}
    } as $vitrine
  }

  response = $vitrine
}
