"""Change 15: a record outside the read contract affects only itself, and every failure is logged."""

import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import httpx
from pydantic import ValidationError
from reflex.istate.data import RouterData
from reflex.state import State

from Projeto_HarleyStore.catalogo_state import CatalogoState, preco_label
from Projeto_HarleyStore.dashboard_state import DashboardState
from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.services.cadastros import (
    Cliente,
    ClienteCreate,
    Fornecedor,
    Funcionario,
    MotoCliente,
    MotoClienteCreate,
    Produto,
    ProdutoCreate,
)
from Projeto_HarleyStore.services.catalogo import ModeloCatalogo, ModeloMoto, VariacaoCor, catalogo_cache
from Projeto_HarleyStore.services.motos import MotoEstoque
from Projeto_HarleyStore.services.ordens_servico import Mecanico
from Projeto_HarleyStore.services.xano_client import (
    XanoClient,
    XanoConnectionError,
    XanoError,
    XanoResponseError,
)
from Projeto_HarleyStore.vendas_state import VendasState, modelo_form, modelo_row

from tests.event_runner import run_event

LOGGER = "Projeto_HarleyStore.services.xano_client"
CORES = [{"nome": "Preto", "hex": "#111111", "imagem_url": "https://cdn.test/p.jpg"}]
MODELO = {"id": 1, "nome_modelo": "Fat Boy", "familia": "CRUISER", "preco_base": "120000.00",
          "imagem_principal": "https://cdn.test/a.jpg", "variacoes_cor": CORES, "ativo": True}
VITRINE = {"id": 1, "nome_modelo": "Fat Boy", "familia": "CRUISER", "variacoes_cor": CORES,
           "preco_a_partir": "120000.00", "disponiveis": 1}
UNIDADE = {"id": 10, "status": "DISPONIVEL", "id_modelo": 1, "nome_modelo": "Fat Boy", "familia": "CRUISER",
           "variacoes_cor": CORES, "chassi": "1HD1BVK12KB123456", "cor": "Preto", "preco_venda": "120000.00"}


@contextmanager
def xano(rotas):
    """Every XanoClient talks to an in-memory Xano: {"path": (status, json)}; nothing leaves the machine."""

    def handler(request):
        caminho = request.url.path.split("/api:test/", 1)[-1]
        if caminho not in rotas:
            return httpx.Response(404, json={"message": "not found"})
        status, corpo = rotas[caminho]
        return httpx.Response(status, json=corpo)

    original = XanoClient.__init__

    def init(self, *, token=None, transport=None, timeout=10.0):
        original(self, token=token, transport=httpx.MockTransport(handler), timeout=timeout)

    with patch.dict(os.environ, {"XANO_API_BASE_URL": "https://xano.test/api:test"}), \
            patch.object(XanoClient, "__init__", init):
        yield


def substate(state_class, role=None, rota="/"):
    root = State(_reflex_internal_init=True)
    root.router = RouterData.from_router_data({"pathname": rota, "query": {}, "asPath": rota, "headers": {}})
    state = root.get_substate(state_class.get_full_name().split("."))
    if role:
        state.is_authenticated, state.employee_role, state.employee_id, state.auth_token = True, role, 2, "jwt"
    return state


class ListReadingTests(unittest.TestCase):
    def test_invalid_record_is_skipped_and_logged_without_its_values(self):
        ruim = {**UNIDADE, "id": 99, "status": "SEGREDO-123"}
        with xano({"motos": (200, [UNIDADE, ruim])}), XanoClient(token="jwt") as client, \
                self.assertLogs(LOGGER, level="WARNING") as logs:
            motos = client.list_motos_estoque()
        self.assertEqual([moto.id for moto in motos], [10])
        log = "\n".join(logs.output)
        self.assertIn("motos: record 1 (id=99) skipped", log)
        self.assertIn("status: literal_error", log)
        self.assertNotIn("SEGREDO-123", log)
        self.assertNotIn("jwt", log)

    def test_contract_breaks_still_raise(self):
        # No valid record means the contract changed: an empty list would hide it.
        for corpo in ([{"id": "x"}], {"items": [UNIDADE]}, None):
            with self.subTest(corpo=corpo), xano({"motos": (200, corpo)}), XanoClient(token="jwt") as client, \
                    self.assertLogs(LOGGER, level="WARNING"), self.assertRaises(XanoResponseError):
                client.list_motos_estoque()
        with xano({"motos": (200, [])}), XanoClient(token="jwt") as client:
            self.assertEqual(client.list_motos_estoque(), [])

    def test_object_payload_outside_the_contract_is_logged(self):
        with xano({"motos/9": (200, {**UNIDADE, "id": 9, "status": "SEGREDO-123"})}), XanoClient(token="jwt") as client, \
                self.assertLogs(LOGGER, level="WARNING") as logs, self.assertRaises(XanoResponseError):
            client.get_moto_estoque(9)
        self.assertNotIn("SEGREDO-123", "\n".join(logs.output))

    def test_server_error_and_network_failure_are_logged_and_typed(self):
        with xano({"motos": (500, {"message": "boom"})}), XanoClient(token="jwt") as client, \
                self.assertLogs(LOGGER, level="ERROR") as logs, self.assertRaises(XanoError) as context:
            client.list_motos_estoque()
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("answered HTTP 500: boom", "\n".join(logs.output))

        def sem_rede(request):
            raise httpx.ConnectError("connection failed", request=request)

        with patch.dict(os.environ, {"XANO_API_BASE_URL": "https://xano.test/api:test"}), \
                XanoClient(token="jwt", transport=httpx.MockTransport(sem_rede)) as client, \
                self.assertLogs(LOGGER, level="WARNING") as logs, self.assertRaises(XanoConnectionError):
            client.list_motos_estoque()
        self.assertNotIn("jwt", "\n".join(logs.output))

    def test_server_error_log_masks_personal_data_and_keeps_a_long_message_cut(self):
        mensagem = (
            "Key (cpf_cnpj)=(12345678900) already exists;\ntel 11987654321; email joao.silva@exemplo.com; "
            "placa ABC1D23; chassi 9BWZZZ377VT004251; linha 12; " + "x" * 300
        )
        with xano({"clientes": (500, {"message": mensagem})}), XanoClient(token="jwt-secreto") as client, \
                self.assertLogs(LOGGER, level="ERROR") as logs, self.assertRaises(XanoError):
            client.list_clientes()
        registro = logs.output[0].split("answered HTTP 500: ", 1)[1]
        self.assertTrue(registro.startswith(
            "Key (cpf_cnpj)=(…) already exists; tel …; email …; placa …; chassi …; linha 12; xxx"
        ))
        self.assertEqual(len(registro), 200)
        self.assertNotRegex(registro, r"\d{3,}|@|\n")
        self.assertNotIn("jwt-secreto", "\n".join(logs.output))

    def test_server_error_with_an_html_body_logs_no_message(self):
        # A proxy 502 answers with HTML: nothing of the body reaches the log.
        def gateway(request):
            return httpx.Response(502, text="<html>Bad gateway 12345678900</html>", headers={"content-type": "text/html"})

        with patch.dict(os.environ, {"XANO_API_BASE_URL": "https://xano.test/api:test"}), \
                XanoClient(token="jwt-secreto", transport=httpx.MockTransport(gateway)) as client, \
                self.assertLogs(LOGGER, level="ERROR") as logs, self.assertRaises(XanoError) as context:
            client.list_motos_estoque()
        self.assertEqual(context.exception.status_code, 502)
        saida = "\n".join(logs.output)
        self.assertIn("answered HTTP 502: sem mensagem", saida)
        self.assertNotIn("html", saida.lower())
        self.assertNotIn("jwt-secreto", saida)


class TolerantReadDtoTests(unittest.TestCase):
    def test_color_read_is_tolerant_but_never_unsafe(self):
        cor = VariacaoCor.model_validate({"nome": None, "hex": "#000", "imagem_url": "javascript:alert(1)"})
        self.assertEqual((cor.nome, cor.hex, cor.imagem_url), ("", "", ""))
        for url in ("https://cdn.test/a.jpg", "http://cdn.test/a.jpg", "/motos/fat-boy/1.fat-boy.jpg"):
            with self.subTest(url=url):
                self.assertEqual(VariacaoCor(nome="Preto", hex="#0b0b0b", imagem_url=url).imagem_url, url)
        self.assertEqual(VariacaoCor(nome="Preto", hex="#0b0b0b", imagem_url="data:image/png;base64,AA").imagem_url, "")

    def test_free_json_colors_and_gallery_read_as_lists(self):
        for cores in ("Preto, Azul", {"nome": "Preto"}, None):
            with self.subTest(cores=cores):
                self.assertEqual(ModeloCatalogo.model_validate({**VITRINE, "variacoes_cor": cores}).variacoes_cor, [])
        modelo = ModeloCatalogo.model_validate(
            {**VITRINE, "variacoes_cor": [{"nome": "Preto", "hex": "#000000"}, "lixo", 3],
             "galeria": [None, "https://cdn.test/1.jpg", 7]}
        )
        self.assertEqual([cor.nome for cor in modelo.variacoes_cor], ["Preto"])
        self.assertEqual(modelo.galeria, ["https://cdn.test/1.jpg"])
        self.assertEqual(MotoEstoque.model_validate({**UNIDADE, "variacoes_cor": "Preto"}).variacoes_cor, [])

    def test_catalog_display_fields_take_defaults(self):
        vitrine = ModeloCatalogo.model_validate({**VITRINE, "nome_modelo": None, "preco_a_partir": None})
        self.assertEqual((vitrine.nome_modelo, vitrine.preco_a_partir), ("", None))
        self.assertEqual(preco_label(vitrine.preco_a_partir), "Preço sob consulta")
        modelo = ModeloMoto.model_validate({**MODELO, "imagem_principal": None, "preco_base": None})
        self.assertEqual(modelo.imagem_principal, "")
        self.assertEqual((modelo_form(modelo)["preco_base"], modelo_row(modelo)["preco_base"]), ("", "—"))

    def test_registration_reads_tolerate_blank_texts(self):
        self.assertEqual(Cliente.model_validate({"id": 1, "nome_cliente": "Ana", "cpf_cnpj": None, "ativo": None}).cpf_cnpj, "")
        self.assertTrue(Cliente.model_validate({"id": 1, "nome_cliente": "Ana", "cpf_cnpj": "", "ativo": None}).ativo)
        moto = MotoCliente.model_validate({"id": 2, "id_cliente": 1, "modelo": None, "placa": "", "chassi": ""})
        self.assertEqual((moto.modelo, moto.placa, moto.chassi), ("", "", ""))
        produto = Produto.model_validate({"id": 3, "codigo": "FLT-001", "nome_produto": None, "categoria": None,
                                          "estoque_qtd": None, "preco_venda": "45.50"})
        self.assertEqual((produto.codigo, produto.nome_produto, produto.estoque_qtd), ("FLT-001", "", 0))
        self.assertEqual(Fornecedor.model_validate({"id": 4, "nome_fornecedor": "Parts", "cnpj": None}).cnpj, "")
        self.assertEqual(Funcionario.model_validate({"id": 5, "nome_funcionario": None, "cargo": None, "tipo": "MECANICO"}).cargo, "")
        self.assertEqual(Mecanico.model_validate({"id": 6, "nome_funcionario": None}).nome_funcionario, "")

    def test_business_rules_still_drop_the_record(self):
        invalidos = (
            (Produto, {"id": 3, "codigo": "P1", "nome_produto": "Filtro", "categoria": "Motor", "preco_venda": 0}),
            (Produto, {"id": 3, "codigo": "P1", "nome_produto": "Filtro", "categoria": "Motor", "preco_venda": None}),
            (MotoCliente, {"id": 2, "id_cliente": None, "modelo": "Iron", "chassi": "CH1"}),
            (Funcionario, {"id": 5, "nome_funcionario": "Ana", "cargo": "x", "tipo": "ESTAGIARIO"}),
            (MotoEstoque, {**UNIDADE, "status": "disponivel"}),
            (ModeloCatalogo, {**VITRINE, "familia": "cruiser"}),
        )
        for modelo, dados in invalidos:
            with self.subTest(modelo=modelo.__name__, dados=dados), self.assertRaises(ValidationError):
                modelo.model_validate(dados)

    def test_writes_keep_every_rule(self):
        for criar in (
            lambda: ClienteCreate(nome_cliente="Ana", cpf_cnpj=""),
            lambda: MotoClienteCreate(id_cliente=1, modelo="Iron", chassi=""),
            lambda: ProdutoCreate(codigo="FLT-001", nome_produto="Filtro", categoria="Motor", preco_venda=10),
        ):
            with self.subTest(), self.assertRaises(ValidationError):
                criar()


class ScreenIsolationTests(unittest.TestCase):
    def setUp(self):
        catalogo_cache.invalidate()
        self.addCleanup(catalogo_cache.invalidate)

    def test_showroom_keeps_the_valid_models(self):
        quebrado = {**VITRINE, "id": 2, "nome_modelo": "Low Rider", "familia": "cruiser"}
        sem_formato = {**VITRINE, "id": 3, "nome_modelo": "Sportster", "variacoes_cor": "Preto, Azul"}
        state = substate(CatalogoState, rota="/catalogo")
        with xano({"catalogo": (200, [VITRINE, quebrado, sem_formato])}), self.assertLogs(LOGGER, level="WARNING"):
            run_event(CatalogoState.load_catalogo, state)
        self.assertEqual(([card.nome for card in state.cards], state.erro), (["Fat Boy", "Sportster"], ""))

    def test_overview_isolates_each_source(self):
        state = substate(DashboardState, "VENDEDOR")
        with xano({"ordens_servico": (200, [{"id": 7, "status": "ABERTA", "id_moto_cliente": 1}]),
                   "motos": (500, {"message": "boom"})}), self.assertLogs(LOGGER, level="ERROR"):
            run_event(DashboardState.load_dashboard, state)
        self.assertEqual((state.kpis.get("os"), "motos" in state.kpis), ("1", False))
        self.assertIn("erro interno", state.kpi_error)

    def test_overview_still_ends_an_expired_session(self):
        state = substate(DashboardState, "VENDEDOR")
        with xano({"ordens_servico": (401, {"message": "expired"}), "motos": (200, [UNIDADE])}):
            run_event(DashboardState.load_dashboard, state)
        self.assertEqual((state.kpis, state.is_authenticated), ({}, False))

    def test_sales_keep_the_units_when_the_models_fail(self):
        state = substate(VendasState, "GERENTE", "/vendas")
        with xano({"motos": (200, [UNIDADE]), "modelos_moto": (500, {"message": "boom"})}), \
                self.assertLogs(LOGGER, level="ERROR"):
            run_event(VendasState.load_vendas, state)
        self.assertEqual(len(state.motos), 1)
        self.assertIn("erro interno", state.list_error)

    def test_sales_skip_only_the_bad_unit(self):
        state = substate(VendasState, "GERENTE", "/vendas")
        with xano({"motos": (200, [UNIDADE, {**UNIDADE, "id": 99, "status": "disponivel"}]),
                   "modelos_moto": (200, [MODELO])}), self.assertLogs(LOGGER, level="WARNING"):
            run_event(VendasState.load_vendas, state)
        self.assertEqual(([row["id"] for row in state.motos], len(state.modelos), state.list_error), (["10"], 1, ""))


class FeedbackTests(unittest.TestCase):
    def test_messages_tell_network_from_data_and_server_errors(self):
        self.assertIn("Sem conexão", error_feedback(XanoConnectionError("Unable to reach the Xano API.")))
        self.assertIn("fora do formato esperado", error_feedback(XanoResponseError("bad payload", status_code=200)))
        self.assertIn("erro interno", error_feedback(XanoError("server", status_code=502)))
        self.assertEqual(error_feedback(XanoError("other")), "Não foi possível comunicar com o Xano. Tente novamente.")


if __name__ == "__main__":
    unittest.main()
