"""Povoamento de demonstração em PRODUÇÃO pela API autenticada, sem duplicar registros.

Cria, se ainda não existirem: 2 fornecedores, 6 peças, 2 entradas de mercadoria, 4 clientes com 1 moto
cada, 3 unidades à venda (1 delas vendida), 2 vendas de balcão e 3 ordens de serviço do mecânico Junior.
Cada passo procura antes o registro pela chave natural (nome, CNPJ/CPF, código, documento, chassi,
placa, descrição da OS); as vendas de balcão usam uma `chave_venda` fixa, que o Xano trata como idempotente.

Travas (o plano Free publica tudo em produção):
    XANO_TEST_LIVE=true .venv/Scripts/python scripts/seed_demo.py            # só lê e mostra o plano
    XANO_TEST_LIVE=true .venv/Scripts/python scripts/seed_demo.py --executar # grava

Credenciais: XANO_TEST_GERENTE_* e XANO_TEST_VENDEDOR_* do `.env` (nunca impressas). O GERENTE cadastra,
dá entrada e opera as OS; o VENDEDOR vende a moto e no balcão, como na loja. Pausa de 2,5 s antes de cada
requisição; um HTTP 429 (nada foi processado) espera 20 s e tenta de novo, até 3 vezes. Se o Xano recusar
uma unidade à venda, ela e a venda de moto ficam como bloqueadas, o resto segue e o script sai com código 1.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from collections import Counter
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Projeto_HarleyStore.dashboard_state import montar_kpis
from Projeto_HarleyStore.formatting import format_currency
from Projeto_HarleyStore.services.balcao import ItemVendaBalcaoCreate, VendaBalcaoCreate
from Projeto_HarleyStore.services.cadastros import (
    ClienteCreate,
    FornecedorCreate,
    MotoClienteCreate,
    ProdutoCreate,
)
from Projeto_HarleyStore.services.entradas import EntradaMercadoriaCreate, ItemEntradaCreate
from Projeto_HarleyStore.services.financeiro import FUSO_LOJA, PeriodoFinanceiro
from Projeto_HarleyStore.services.motos import MotoEstoqueCreate, VendaMotoCreate
from Projeto_HarleyStore.services.ordens_servico import (
    ItemOSCreate,
    OrdemServicoCreate,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import XanoClient, XanoRateLimitError, XanoValidationError

PAUSA = 2.5
ESPERA_429 = 20
TENTATIVAS_429 = 3
CENTAVO = Decimal("0.01")


# ----- documentos válidos (dígitos verificadores) -----


def _dv_mod11(digitos: str, pesos: list[int]) -> str:
    resto = sum(int(d) * p for d, p in zip(digitos, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cpf(base9: str) -> str:
    d1 = _dv_mod11(base9, list(range(10, 1, -1)))
    d2 = _dv_mod11(base9 + d1, list(range(11, 1, -1)))
    n = base9 + d1 + d2
    return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"


def cnpj(base12: str) -> str:
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _dv_mod11(base12, pesos)
    d2 = _dv_mod11(base12 + d1, [6, *pesos])
    n = base12 + d1 + d2
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


_VIN_VALOR = {**{str(d): d for d in range(10)}, **dict(zip("ABCDEFGH", range(1, 9), strict=True)),
              **dict(zip("JKLMN", range(1, 6), strict=True)), "P": 7, "R": 9,
              **dict(zip("STUVWXYZ", range(2, 10), strict=True))}
_VIN_PESOS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def vin(prefixo8: str, ano: str, fabrica: str, serie6: str) -> str:
    """VIN de 17 caracteres com o dígito verificador (posição 9) calculado."""
    sem_dv = prefixo8 + "0" + ano + fabrica + serie6
    resto = sum(_VIN_VALOR[c] * p for c, p in zip(sem_dv, _VIN_PESOS, strict=True)) % 11
    return prefixo8 + ("X" if resto == 10 else str(resto)) + ano + fabrica + serie6


FLUXO_OS = ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA"]


def avanca(atual: str, alvo: str) -> bool:
    """Só move a OS para a frente; numa nova execução, uma OS concluída ou cancelada fica como está."""
    return atual in FLUXO_OS and FLUXO_OS.index(atual) < FLUXO_OS.index(alvo)


def _autoteste() -> None:
    # Exemplos públicos sabidamente válidos de cada algoritmo.
    assert cpf("529982247") == "529.982.247-25"
    assert cnpj("114447770001") == "11.444.777/0001-61"
    assert vin("1M8GDM9A", "K", "P", "042788") == "1M8GDM9AXKP042788"
    assert avanca("ABERTA", "EM_ANDAMENTO") and avanca("EM_ANDAMENTO", "CONCLUIDA")
    assert not avanca("CONCLUIDA", "EM_ANDAMENTO") and not avanca("EM_ANDAMENTO", "EM_ANDAMENTO")
    assert not avanca("CANCELADA", "CONCLUIDA")


# ----- dados de demonstração -----

FORNECEDORES = [
    {"nome_fornecedor": "HD Parts Distribuidora Ltda", "cnpj": cnpj("348712560001"), "contato": "Patrícia Lemos · (11) 3061-4480"},
    {"nome_fornecedor": "Custom Garage Importações", "cnpj": cnpj("275304180001"), "contato": "Eduardo Santana · (41) 3029-7715"},
]

# codigo, nome, descrição, categoria, preço de venda, fornecedor da entrada, quantidade, custo unitário
PECAS = [
    ("OLE20W50SIN", "Óleo Sintético 20W50 (1L)", "Óleo sintético 20W50 para motores V-Twin, embalagem de 1 litro.", "Lubrificantes", "89.90", 0, 40, "54.00"),
    ("FILOLECROM", "Filtro de Óleo Cromado", "Filtro de óleo com acabamento cromado para motores Milwaukee-Eight e Twin Cam.", "Filtros", "129.90", 0, 20, "72.50"),
    ("VELAIRID", "Vela de Ignição Iridium", "Vela de ignição com eletrodo de irídio, de alta durabilidade.", "Ignição", "79.90", 0, 30, "38.00"),
    ("PASTFREDIA", "Pastilha de Freio Dianteira", "Jogo de pastilhas sinterizadas para a pinça dianteira.", "Freios", "289.90", 1, 16, "168.00"),
    # Saldo baixo de propósito (2 unidades); nenhuma venda ou OS da demonstração consome esta peça.
    ("KITJUNPRIM", "Kit Junta da Primária", "Kit de juntas e anel de vedação da tampa da primária.", "Transmissão", "189.90", 1, 2, "104.00"),
    ("FLUFREDOT4", "Fluido de Freio DOT 4", "Fluido de freio DOT 4 de alto ponto de ebulição, frasco de 355 ml.", "Freios", "59.90", 1, 24, "29.90"),
]
DOCUMENTOS = ["NF-248913", "NF-071552"]  # entrada de cada fornecedor, na ordem de FORNECEDORES

CLIENTES = [
    {"nome_cliente": "Marcos Vinícius Albuquerque", "cpf_cnpj": cpf("397451820"), "telefone": "(11) 98734-2261",
     "email": "marcos.albuquerque@example.com", "endereco": "Rua Haddock Lobo, 1180 — Cerqueira César, São Paulo/SP"},
    {"nome_cliente": "Fernanda Ribeiro Costa", "cpf_cnpj": cpf("284613957"), "telefone": "(41) 99812-4470",
     "email": "fernanda.costa@example.com", "endereco": "Av. Sete de Setembro, 4210 — Batel, Curitiba/PR"},
    {"nome_cliente": "Rafael Henrique Moreira", "cpf_cnpj": cpf("165038742"), "telefone": "(31) 99145-6082",
     "email": "rafael.moreira@example.com", "endereco": "Rua Pernambuco, 935 — Savassi, Belo Horizonte/MG"},
    {"nome_cliente": "Juliana Carvalho Mendes", "cpf_cnpj": cpf("452907316"), "telefone": "(19) 99276-3318",
     "email": "juliana.mendes@example.com", "endereco": "Rua Coronel Quirino, 1520 — Cambuí, Campinas/SP"},
]
# Uma moto por cliente, na ordem de CLIENTES.
MOTOS_CLIENTES = [
    {"modelo": "Fat Boy", "placa": "FJD4E21", "chassi": vin("1HD1YGK2", "K", "C", "014532")},
    {"modelo": "Road King", "placa": "RTK2B47", "chassi": vin("1HD1FBM1", "M", "B", "623418")},
    {"modelo": "Iron 883", "placa": "PXV8C83", "chassi": vin("1HD4LE23", "L", "C", "418265")},
    {"modelo": "Heritage Classic", "placa": "SBA5D19", "chassi": vin("1HD1YDJ1", "N", "B", "037714")},
]

# Unidades à venda: nome do modelo no catálogo, cor, ano, preço e chassi (2026 = "T" na posição 10).
UNIDADES = [
    {"modelo": "Breakout", "cor": "Preto Vivid", "ano": 2026, "preco": "139950.00", "chassi": vin("1HD1YTF1", "T", "B", "702144")},
    {"modelo": "Fat Boy", "cor": "Vermelho", "ano": 2026, "preco": "139900.00", "chassi": vin("1HD1YGK2", "T", "C", "702187")},
    {"modelo": "Sportster", "cor": "Grafite", "ano": 2026, "preco": "79900.00", "chassi": vin("1HD1ZFS1", "T", "B", "702203")},
]
VENDA_MOTO = {"modelo": "Sportster", "cliente": 2}  # índice em CLIENTES (Rafael)

# Vendas de balcão: chave fixa (idempotente no Xano), cliente (índice ou None) e itens (código, quantidade).
BALCAO = [
    {"chave": "harleystore/demo/balcao/1", "cliente": 1, "itens": [("OLE20W50SIN", 4), ("FILOLECROM", 1), ("VELAIRID", 2)]},
    {"chave": "harleystore/demo/balcao/2", "cliente": None, "itens": [("PASTFREDIA", 1), ("FLUFREDOT4", 2)]},
]

MECANICO = "junior"
# OS: moto (índice em MOTOS_CLIENTES), tipo, descrição, km e os passos até o estado final.
ORDENS = [
    {"moto": 0, "tipo": "PREVENTIVA", "km": 20340,
     "descricao": "Revisão geral dos 20.000 km: troca de óleo e filtro, inspeção de freios, correia e suspensão.",
     "passos": []},
    {"moto": 1, "tipo": "CORRETIVA", "km": 31870,
     "descricao": "Ruído metálico ao frear e pedal do freio dianteiro esponjoso.",
     "passos": [("status", "EM_ANDAMENTO"),
                ("itens", [("PECA", "PASTFREDIA", 1), ("PECA", "FLUFREDOT4", 1),
                           ("SERVICO", "Substituição das pastilhas e sangria do freio dianteiro", "220.00")])]},
    {"moto": 3, "tipo": "PREVENTIVA", "km": 10120,
     "descricao": "Revisão dos 10.000 km com troca de óleo do motor.",
     "passos": [("status", "EM_ANDAMENTO"),
                ("itens", [("PECA", "OLE20W50SIN", 4), ("SERVICO", "Mão de obra da troca de óleo e inspeção geral", "180.00")]),
                ("status", "CONCLUIDA")]},
]


# ----- execução -----


def chamar(funcao, *args):
    """Uma requisição com a pausa do plano Free; 429 não processa nada, então repetir é seguro."""
    for tentativa in range(1, TENTATIVAS_429 + 1):
        time.sleep(PAUSA)
        try:
            return funcao(*args)
        except XanoRateLimitError:
            if tentativa == TENTATIVAS_429:
                raise
            print(f"   429: aguardando {ESPERA_429} s (tentativa {tentativa})")
            time.sleep(ESPERA_429)
    return None



class Povoamento:
    def __init__(self, gerente: XanoClient, vendedor: XanoClient, executar: bool) -> None:
        self.gerente, self.vendedor, self.executar = gerente, vendedor, executar
        self.contagem: Counter[tuple[str, str]] = Counter()
        self.inicio = time.time()  # recibo de balcão anterior a isto = chave de uma execução passada

    def gravar(self, modulo: str, descricao: str, funcao, *args, ja_existia=None):
        if not self.executar:
            self.contagem[(modulo, "a criar")] += 1
            print(f"   [plano] criaria {descricao}")
            return None
        resultado = chamar(funcao, *args)
        if ja_existia is not None and ja_existia(resultado):
            self.existente(modulo, descricao)
        else:
            self.contagem[(modulo, "criados")] += 1
            print(f"   criado: {descricao}")
        return resultado

    def pendente(self, modulo: str, descricao: str) -> None:
        """Depende de um registro que só existe após uma gravação: conta no plano; ao executar, é defeito."""
        if self.executar:
            raise SystemExit(f"Interrompido: {modulo} — {descricao}. Corrija e rode de novo (o script não duplica).")
        self.contagem[(modulo, "a criar")] += 1
        print(f"   [plano] criaria {descricao}")

    def bloqueado(self, modulo: str, descricao: str, motivo: object) -> None:
        self.contagem[(modulo, "bloqueados")] += 1
        print(f"   BLOQUEADO: {descricao} — {motivo}")

    def existente(self, modulo: str, descricao: str) -> None:
        self.contagem[(modulo, "já existiam")] += 1
        print(f"   já existe: {descricao}")

    def rodar(self) -> None:
        g = self.gerente
        print("1. Fornecedores e peças")
        fornecedores = chamar(g.list_fornecedores)
        ids_fornecedor = []
        for dados in FORNECEDORES:
            achado = next((f for f in fornecedores if f.nome_fornecedor.casefold() == dados["nome_fornecedor"].casefold()
                           or f.cnpj == dados["cnpj"]), None)
            if achado:
                self.existente("Fornecedores", dados["nome_fornecedor"])
            else:
                achado = self.gravar("Fornecedores", dados["nome_fornecedor"], g.create_fornecedor, FornecedorCreate(**dados))
            ids_fornecedor.append(achado.id if achado else None)

        produtos = chamar(g.list_produtos)
        for codigo, nome, descricao, categoria, preco, *_ in PECAS:
            achado = next((p for p in produtos if p.codigo.casefold() == codigo.casefold()
                           or p.nome_produto.casefold() == nome.casefold()), None)
            if achado:
                self.existente("Peças", nome)
            else:
                criado = self.gravar("Peças", nome, g.create_produto, ProdutoCreate(
                    codigo=codigo, nome_produto=nome, descricao=descricao, categoria=categoria, preco_venda=Decimal(preco)))
                if criado:
                    produtos.append(criado)
        por_codigo = {p.codigo.casefold(): p for p in produtos}

        print("2. Entradas de mercadoria")
        entradas = chamar(g.list_entradas)
        for indice, documento in enumerate(DOCUMENTOS):
            id_fornecedor = ids_fornecedor[indice]
            if any(e.numero_documento == documento and e.id_fornecedor == id_fornecedor for e in entradas):
                self.existente("Entradas de mercadoria", documento)
                continue
            itens = [ItemEntradaCreate(id_produto=por_codigo[c.casefold()].id, quantidade=q, valor_unitario=Decimal(custo))
                     for c, *_, forn, q, custo in PECAS if forn == indice and c.casefold() in por_codigo]
            if id_fornecedor is None or len(itens) != sum(1 for p in PECAS if p[5] == indice):
                self.pendente("Entradas de mercadoria", f"{documento} (depende de fornecedor e peças novos)")
                continue
            self.gravar("Entradas de mercadoria", f"{documento} com {len(itens)} itens", g.registrar_entrada,
                        EntradaMercadoriaCreate(id_fornecedor=id_fornecedor, numero_documento=documento, itens=itens))

        print("3. Clientes e motos de clientes")
        clientes = chamar(g.list_clientes)
        motos_cli = chamar(g.list_motos_clientes)
        ids_cliente, ids_moto_cliente = [], []
        for dados, moto in zip(CLIENTES, MOTOS_CLIENTES, strict=True):
            achado = next((c for c in clientes if c.cpf_cnpj == dados["cpf_cnpj"]
                           or c.nome_cliente.casefold() == dados["nome_cliente"].casefold()), None)
            if achado:
                self.existente("Clientes", dados["nome_cliente"])
            else:
                achado = self.gravar("Clientes", dados["nome_cliente"], g.create_cliente, ClienteCreate(**dados))
            ids_cliente.append(achado.id if achado else None)
            moto_achada = next((m for m in motos_cli if m.chassi == moto["chassi"] or (m.placa or "") == moto["placa"]), None)
            if moto_achada:
                self.existente("Motos de clientes", f"{moto['modelo']} {moto['placa']}")
            elif achado:
                moto_achada = self.gravar("Motos de clientes", f"{moto['modelo']} {moto['placa']}", g.create_moto_cliente,
                                          MotoClienteCreate(id_cliente=achado.id, **moto))
            else:
                self.pendente("Motos de clientes", f"{moto['modelo']} {moto['placa']} (depende do cliente novo)")
            ids_moto_cliente.append(moto_achada.id if moto_achada else None)

        print("4. Unidades à venda e venda de 1 moto")
        modelos = {m.nome_modelo.casefold(): m for m in chamar(g.list_modelos_moto) if m.ativo}
        unidades = chamar(g.list_motos_estoque)
        unidade_por_modelo = {}
        for dados in UNIDADES:
            modelo = modelos.get(dados["modelo"].casefold())
            if modelo is None:
                raise SystemExit(f"Modelo {dados['modelo']!r} não está ativo no catálogo; nada foi criado para ele.")
            achada = next((u for u in unidades if (u.chassi or "").upper() == dados["chassi"]), None)
            if achada:
                self.existente("Unidades à venda", f"{dados['modelo']} {dados['ano']}")
            else:
                try:
                    achada = self.gravar("Unidades à venda", f"{dados['modelo']} {dados['ano']} {dados['cor']}",
                                         g.cadastrar_moto_estoque,
                                         MotoEstoqueCreate(id_modelo=modelo.id, chassi=dados["chassi"], cor=dados["cor"],
                                                           ano_modelo=dados["ano"], preco_venda=Decimal(dados["preco"])))
                except XanoValidationError as erro:
                    # Recusa de validação não grava nada; o que não depende desta unidade segue.
                    self.bloqueado("Unidades à venda", f"{dados['modelo']} {dados['ano']}", erro)
            unidade_por_modelo[dados["modelo"]] = achada

        vendida = unidade_por_modelo.get(VENDA_MOTO["modelo"])
        id_cliente = ids_cliente[VENDA_MOTO["cliente"]]
        if vendida is not None and vendida.status == "VENDIDA":
            self.existente("Vendas de moto", f"{VENDA_MOTO['modelo']} já vendida")
        elif vendida is not None and id_cliente is not None:
            preco = next(Decimal(u["preco"]) for u in UNIDADES if u["modelo"] == VENDA_MOTO["modelo"])
            self.gravar("Vendas de moto", f"{VENDA_MOTO['modelo']} para {CLIENTES[VENDA_MOTO['cliente']]['nome_cliente']}",
                        self.vendedor.vender_moto, VendaMotoCreate(id_moto=vendida.id, id_cliente=id_cliente, valor_venda=preco))
        elif self.executar and vendida is None:
            self.bloqueado("Vendas de moto", VENDA_MOTO["modelo"], "a unidade à venda não foi cadastrada")
        else:
            self.pendente("Vendas de moto", f"{VENDA_MOTO['modelo']} (depende da unidade e do cliente novos)")

        print("5. Vendas de balcão")
        precos = {p.codigo.casefold(): p for p in chamar(g.list_produtos)}
        for venda in BALCAO:
            if any(c.casefold() not in precos for c, _ in venda["itens"]):
                self.pendente("Vendas de balcão", f"{venda['chave']} (depende das peças novas)")
                continue
            itens = [ItemVendaBalcaoCreate(id_produto=precos[c.casefold()].id, quantidade=q) for c, q in venda["itens"]]
            # O total que o vendedor vê: cada linha arredondada a centavos, como o Xano recalcula.
            total = sum(((precos[c.casefold()].preco_venda * q).quantize(CENTAVO, ROUND_HALF_UP) for c, q in venda["itens"]),
                        Decimal("0"))
            cliente = ids_cliente[venda["cliente"]] if venda["cliente"] is not None else None
            # Mesma chave = mesma venda: repetir o script devolve a venda já gravada, sem nova baixa.
            chave = str(uuid.uuid5(uuid.NAMESPACE_URL, venda["chave"]))
            self.gravar("Vendas de balcão", f"{len(itens)} itens, {format_currency(total)}", self.vendedor.vender_balcao,
                        VendaBalcaoCreate(chave_venda=chave, id_cliente=cliente, total_esperado=total, itens=itens),
                        ja_existia=lambda recibo: recibo.data_transacao.timestamp() < self.inicio)

        print("6. Ordens de serviço")
        mecanico = next((m for m in chamar(g.list_mecanicos) if MECANICO in m.nome_funcionario.casefold()), None)
        if mecanico is None:
            raise SystemExit("Mecânico Junior ativo não encontrado; nenhuma OS foi criada.")
        for ordem in ORDENS:
            self.ordem(ordem, ids_moto_cliente[ordem["moto"]], mecanico.id, precos)

    def ordem(self, ordem: dict, id_moto: int | None, id_mecanico: int, precos: dict) -> None:
        g = self.gerente
        rotulo = ordem["descricao"][:48] + "…"
        if id_moto is None:
            self.pendente("Ordens de serviço", f"{rotulo} (depende da moto nova)")
            return
        existentes = chamar(lambda: g.list_ordens_servico(id_moto_cliente=id_moto))
        achada = next((o for o in existentes if (o.descricao_problema or "").strip() == ordem["descricao"]), None)
        if achada:
            self.existente("Ordens de serviço", rotulo)
            detalhe = chamar(g.get_ordem_servico, achada.id)
        else:
            detalhe = self.gravar("Ordens de serviço", rotulo, g.abrir_ordem_servico, OrdemServicoCreate(
                id_moto_cliente=id_moto, id_mecanico=id_mecanico, tipo_servico=ordem["tipo"],
                descricao_problema=ordem["descricao"], quilometragem=ordem["km"]))
        for passo, valor in ordem["passos"]:
            if detalhe is None:  # plano: a OS ainda não existe
                self.pendente("Passos de OS", f"{passo} {valor if passo == 'status' else len(valor)}")
                continue
            if passo == "status":
                if not avanca(detalhe.status, valor):
                    continue
                detalhe = self.gravar("Passos de OS", f"OS {detalhe.id}: {detalhe.status} → {valor}", g.transicionar_ordem_servico,
                                      detalhe.id, TransicaoStatusOS(status_atual=detalhe.status, status_novo=valor)) or detalhe
                continue
            for item in valor:
                if detalhe.status not in ("ABERTA", "EM_ANDAMENTO"):
                    break
                if item[0] == "PECA":
                    produto = precos[item[1].casefold()]
                    if any(i.id_produto == produto.id for i in detalhe.itens):
                        continue
                    novo = ItemOSCreate(tipo_item="PECA", id_produto=produto.id, quantidade=item[2])
                    rotulo_item = f"{item[2]}× {produto.nome_produto}"
                else:
                    if any(i.tipo_item == "SERVICO" and (i.descricao or "") == item[1] for i in detalhe.itens):
                        continue
                    novo = ItemOSCreate(tipo_item="SERVICO", descricao=item[1], quantidade=1, valor_unitario=Decimal(item[2]))
                    rotulo_item = f"mão de obra {format_currency(Decimal(item[2]))}"
                detalhe = self.gravar("Itens de OS", f"OS {detalhe.id}: {rotulo_item}", g.adicionar_item_ordem_servico,
                                      detalhe.id, novo) or detalhe

    def resumo(self) -> None:
        g = self.gerente
        hoje = datetime.now(FUSO_LOJA).date()
        mes = chamar(g.resumo_financeiro, PeriodoFinanceiro(inicio=hoje.replace(day=1), fim=hoje))
        ordens = chamar(g.list_ordens_servico)
        motos = chamar(g.list_motos_estoque)
        produtos = chamar(g.list_produtos)
        kpis = montar_kpis(ordens, motos, mes)
        print("\n=== Registros por módulo ===")
        for modulo in dict.fromkeys(m for m, _ in self.contagem):
            partes = [f"{estado}: {self.contagem[(modulo, estado)]}" for estado in ("criados", "a criar", "já existiam", "bloqueados")
                      if self.contagem[(modulo, estado)]]
            print(f"{modulo:24} {' | '.join(partes)}")
        print("\n=== Financeiro (mês até hoje) ===")
        print(f"receitas {format_currency(mes.receitas)} | despesas {format_currency(mes.despesas)} | saldo {format_currency(mes.saldo)}")
        for total in mes.por_tipo:
            print(f"  {total.tipo:20} {total.natureza:8} {total.quantidade:3} operações  {format_currency(total.valor)}")
        print("\n=== Visão geral (cartões do GERENTE) ===")
        print(f"Faturamento do mês: {kpis['faturamento']} ({kpis['faturamento_detalhe']})")
        print(f"Vendas de balcão: {kpis['balcao']} ({kpis['balcao_detalhe']})")
        print(f"Motos em estoque: {kpis['motos']} ({kpis['motos_detalhe']})")
        print(f"OS ativas: {kpis['os']} ({kpis['os_detalhe']})")
        baixo = [(p.nome_produto, p.estoque_qtd) for p in produtos if p.ativo and p.estoque_qtd <= 2]
        print(f"Peças com saldo até 2: {baixo or 'nenhuma'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--executar", action="store_true", help="grava no Xano de produção (sem ele, só mostra o plano)")
    args = parser.parse_args()
    if os.environ.get("XANO_TEST_LIVE", "").strip().lower() != "true":
        print("Recusado: defina XANO_TEST_LIVE=true. Este script lê e grava no Xano de produção.")
        return 2
    _autoteste()
    ambiente = {**dotenv_values(ROOT / ".env"), **{k: v for k, v in os.environ.items() if k.startswith("XANO_")}}
    for chave in ("XANO_API_BASE_URL", "XANO_AUTH_API_BASE_URL"):
        if ambiente.get(chave):
            os.environ[chave] = ambiente[chave]
    credenciais = {papel: (ambiente.get(f"XANO_TEST_{papel}_EMAIL"), ambiente.get(f"XANO_TEST_{papel}_PASSWORD"))
                   for papel in ("GERENTE", "VENDEDOR")}
    if not all(all(par) for par in credenciais.values()):
        print("Recusado: faltam XANO_TEST_GERENTE_* ou XANO_TEST_VENDEDOR_* no .env.")
        return 2
    tokens = {}
    for papel, (email, senha) in credenciais.items():
        with XanoClient() as cliente:
            tokens[papel] = chamar(cliente.login, email, senha)["authToken"]
    print(f"Modo: {'EXECUTAR (grava em produção)' if args.executar else 'PLANO (somente leitura)'}")
    with XanoClient(token=tokens["GERENTE"]) as gerente, XanoClient(token=tokens["VENDEDOR"]) as vendedor:
        povoamento = Povoamento(gerente, vendedor, args.executar)
        povoamento.rodar()
        povoamento.resumo()
    return 1 if any(estado == "bloqueados" for _, estado in povoamento.contagem) else 0


if __name__ == "__main__":
    sys.exit(main())
