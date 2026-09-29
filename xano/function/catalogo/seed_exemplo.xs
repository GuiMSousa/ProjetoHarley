// Popula o catálogo com dados de exemplo (Change 8): um modelo por família, com cores e
// unidades em estoque. Idempotente: não faz nada se já existir algum modelo.
// Executar uma vez no Xano (Run & Debug), informando o id do funcionário GERENTE que
// constará como autor do histórico. As imagens são placeholders neutros (placehold.co):
// substitua-as por fotos próprias ou licenciadas da loja antes de abrir a vitrine ao público.
function "Catalogo/seed_exemplo" {
  input {
    int id_funcionario filters=min:1
  }

  stack {
    db.query modelos_moto {
      return = {type: "exists"}
    } as $ja_populado

    var $criados {
      value = 0
    }

    conditional {
      if (!$ja_populado) {
        var $exemplos {
          value = [
            {
              nome_modelo     : "Street Glide"
              familia         : "TOURING"
              descricao       : "Touring de estrada com carenagem batwing, bagageiros e conforto para longas distâncias."
              preco_base      : 189900
              imagem_principal: "https://placehold.co/1600x1000/0B0B0B/FF6600/png?text=Street+Glide"
              destaque        : true
              variacoes_cor   : [
                {nome: "Vivid Black", hex: "#0B0B0B", imagem_url: "https://placehold.co/1600x1000/0B0B0B/FF6600/png?text=Street+Glide"}
                {nome: "Laranja Harley", hex: "#FF6600", imagem_url: "https://placehold.co/1600x1000/FF6600/000000/png?text=Street+Glide"}
                {nome: "Prata Metálico", hex: "#A0A0A0", imagem_url: "https://placehold.co/1600x1000/A0A0A0/000000/png?text=Street+Glide"}
              ]
              unidades        : [
                {chassi: "1HD1KTP19RB600001", cor: "Vivid Black", ano_modelo: 2025, preco_venda: 189900}
                {chassi: "1HD1KTP19RB600002", cor: "Laranja Harley", ano_modelo: 2025, preco_venda: 192500}
              ]
            }
            {
              nome_modelo     : "Fat Boy"
              familia         : "CRUISER"
              descricao       : "Cruiser de presença marcante, rodas sólidas e motor de alto torque."
              preco_base      : 139900
              imagem_principal: "https://placehold.co/1600x1000/1A1A1A/FFFFFF/png?text=Fat+Boy"
              destaque        : false
              variacoes_cor   : [
                {nome: "Preto Fosco", hex: "#1A1A1A", imagem_url: "https://placehold.co/1600x1000/1A1A1A/FFFFFF/png?text=Fat+Boy"}
                {nome: "Vermelho", hex: "#8B1E1E", imagem_url: "https://placehold.co/1600x1000/8B1E1E/FFFFFF/png?text=Fat+Boy"}
              ]
              unidades        : [
                {chassi: "1HD1YGK15RB600003", cor: "Preto Fosco", ano_modelo: 2025, preco_venda: 139900}
              ]
            }
            {
              nome_modelo     : "Pan America"
              familia         : "ADVENTURE"
              descricao       : "Adventure touring para asfalto e terra, com suspensão de longo curso."
              preco_base      : 129900
              imagem_principal: "https://placehold.co/1600x1000/3F4A3C/FFFFFF/png?text=Pan+America"
              destaque        : false
              variacoes_cor   : [
                {nome: "Verde Militar", hex: "#3F4A3C", imagem_url: "https://placehold.co/1600x1000/3F4A3C/FFFFFF/png?text=Pan+America"}
                {nome: "Branco", hex: "#E5E5E5", imagem_url: "https://placehold.co/1600x1000/E5E5E5/000000/png?text=Pan+America"}
              ]
              unidades        : [
                {chassi: "1HD1RHF13RB600004", cor: "Verde Militar", ano_modelo: 2025, preco_venda: 129900}
              ]
            }
            {
              nome_modelo     : "Nightster"
              familia         : "SPORT"
              descricao       : "Sport ágil e leve, com posição de pilotagem esportiva."
              preco_base      : 79900
              imagem_principal: "https://placehold.co/1600x1000/2E2E2E/FF6600/png?text=Nightster"
              destaque        : false
              variacoes_cor   : [
                {nome: "Grafite", hex: "#2E2E2E", imagem_url: "https://placehold.co/1600x1000/2E2E2E/FF6600/png?text=Nightster"}
              ]
              unidades        : []
            }
          ]
        }

        foreach ($exemplos) {
          each as $exemplo {
            db.add modelos_moto {
              data = {
                nome_modelo     : $exemplo.nome_modelo
                familia         : $exemplo.familia
                descricao       : $exemplo.descricao
                preco_base      : $exemplo.preco_base
                imagem_principal: $exemplo.imagem_principal
                variacoes_cor   : $exemplo.variacoes_cor
                destaque        : $exemplo.destaque
                ativo           : true
                created_at      : now
              }
            } as $modelo

            var.update $criados {
              value = $criados + 1
            }

            foreach ($exemplo.unidades) {
              each as $unidade {
                db.add motos {
                  data = {
                    id_modelo    : $modelo.id
                    marca        : "Harley-Davidson"
                    modelo       : $modelo.nome_modelo
                    chassi       : $unidade.chassi
                    cor          : $unidade.cor
                    ano_modelo   : $unidade.ano_modelo
                    preco_venda  : $unidade.preco_venda
                    status       : "DISPONIVEL"
                    versao_status: 1
                    atualizado_em: now
                    created_at   : now
                  }
                } as $moto

                db.add historico_status_moto {
                  data = {
                    id_moto        : $moto.id
                    status_novo    : "DISPONIVEL"
                    versao_anterior: 0
                    id_funcionario : $input.id_funcionario
                    observacao     : "Dados de exemplo"
                    created_at     : now
                  }
                } as $historico
              }
            }
          }
        }
      }
    }
  }

  response = {modelos_criados: $criados}
}
