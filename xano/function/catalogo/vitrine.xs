// Projeção de vitrine do catálogo: somente campos públicos de modelos ativos.
// Nunca inclui unidades, chassi, cliente, vendedor nem histórico.
// "A partir de" é o menor preço entre as unidades DISPONIVEL do modelo; sem unidades,
// vale o preço base. As unidades são lidas numa única consulta (sem N+1).
function "Catalogo/vitrine" {
  input {
    text? familia?
    text? busca?
    int? modelo_id?
  }

  stack {
    db.query modelos_moto {
      where = $db.modelos_moto.ativo != false && $db.modelos_moto.familia ==? $input.familia && $db.modelos_moto.id ==? $input.modelo_id
      sort = {destaque: "desc", nome_modelo: "asc"}
      return = {type: "list"}
    } as $modelos

    db.query motos {
      where = $db.motos.status == "DISPONIVEL" && $db.motos.id_modelo != null
      output = ["id_modelo", "preco_venda"]
      return = {type: "list"}
    } as $unidades

    var $vitrine {
      value = []
    }

    var $disponiveis {
      value = 0
    }

    var $menor_preco {
      value = null
    }

    var $busca {
      value = $input.busca ?? ""
    }

    var $card {
      value = {}
    }

    foreach ($modelos) {
      each as $modelo {
        var.update $disponiveis {
          value = 0
        }

        var.update $menor_preco {
          value = null
        }

        foreach ($unidades) {
          each as $unidade {
            conditional {
              if ($unidade.id_modelo == $modelo.id) {
                var.update $disponiveis {
                  value = $disponiveis + 1
                }

                conditional {
                  if ($menor_preco == null || $unidade.preco_venda < $menor_preco) {
                    var.update $menor_preco {
                      value = $unidade.preco_venda
                    }
                  }
                }
              }
            }
          }
        }

        conditional {
          if ($busca == "" || ($modelo.nome_modelo|icontains:$busca)) {
            var.update $card {
              value = {
                id              : $modelo.id
                nome_modelo     : $modelo.nome_modelo
                familia         : $modelo.familia
                descricao       : $modelo.descricao
                imagem_principal: $modelo.imagem_principal
                galeria         : ($modelo.galeria ?? [])|map:$$.path
                variacoes_cor   : $modelo.variacoes_cor ?? []
                destaque        : $modelo.destaque ?? false
                preco_a_partir  : $menor_preco ?? $modelo.preco_base
                disponiveis     : $disponiveis
              }
            }

            var.update $vitrine {
              value = $vitrine|push:$card
            }
          }
        }
      }
    }
  }

  response = $vitrine
  guid = "V4Zr-kM9kM8R5liNZrhQyicCjd4"
}
