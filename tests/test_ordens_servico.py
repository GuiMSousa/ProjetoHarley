import json
import os
import unittest
from decimal import Decimal
from itertools import product
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.ordens_servico import (
    TRANSICOES_OS,
    ItemOrdemServico,
    ItemOSCreate,
    OrdemServicoCreate,
    OrdemServicoDetalhe,
    OrdemServicoResumo,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoClient,
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)


STATUSES = ("ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA")
VALID_TRANSITIONS = {
    ("ABERTA", "EM_ANDAMENTO"),
    ("ABERTA", "CANCELADA"),
    ("EM_ANDAMENTO", "CONCLUIDA"),
    ("EM_ANDAMENTO", "CANCELADA"),
}

DETAIL_RESPONSE = {
    "id": 31,
    "status": "EM_ANDAMENTO",
    "id_moto_cliente": 12,
    "data_abertura": 1790000000000,
    "data_inicio": 1790000600000,
    "tipo_servico": "CORRETIVA",
    "descricao_problema": "Ruído na embreagem",
    "quilometragem": 18350,
    "id_cliente": 5,
    "nome_cliente": "Ana Souza",
    "placa": "ABC1D23",
    "modelo": "Street Glide",
    "id_funcionario": 2,
    "nome_funcionario": "Carlos",
    "id_mecanico": 4,
    "nome_mecanico": "Bruno",
    "historico": [
        {"id": 1, "status_anterior": None, "status_novo": "ABERTA", "id_funcionario": 2,
         "nome_funcionario": "Carlos", "created_at": 1790000000000, "observacao": None},
        {"id": 2, "status_anterior": "ABERTA", "status_novo": "EM_ANDAMENTO", "id_funcionario": 4,
         "nome_funcionario": "Bruno", "created_at": 1790000600000},
    ],
    "itens": [],
}


def abertura(**overrides):
    data = {
        "id_moto_cliente": 12,
        "id_mecanico": 4,
        "tipo_servico": "CORRETIVA",
        "descricao_problema": "  Ruído na embreagem  ",
        "quilometragem": 18350,
    }
    data.update(overrides)
    return OrdemServicoCreate(**data)


class OrdemServicoDtoTests(unittest.TestCase):
    def test_valid_opening_strips_description(self):
        self.assertEqual(abertura().descricao_problema, "Ruído na embreagem")

    def test_opening_rejects_invalid_fields(self):
        invalid = [
            {"tipo_servico": "REVISAO"},
            {"descricao_problema": "   "},
            {"quilometragem": -1},
            {"id_moto_cliente": 0},
            {"id_mecanico": 0},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                abertura(**overrides)

    def test_mechanic_and_mileage_are_optional(self):
        ordem = abertura(id_mecanico=None, quilometragem=None)
        self.assertIsNone(ordem.id_mecanico)
        self.assertIsNone(ordem.quilometragem)

    def test_transition_table_mirrors_the_state_machine(self):
        for atual, novo in product(STATUSES, STATUSES):
            with self.subTest(atual=atual, novo=novo):
                observacao = "Cliente desistiu" if novo == "CANCELADA" else None
                if (atual, novo) in VALID_TRANSITIONS:
                    TransicaoStatusOS(status_atual=atual, status_novo=novo, observacao=observacao)
                else:
                    with self.assertRaises(ValidationError):
                        TransicaoStatusOS(status_atual=atual, status_novo=novo, observacao=observacao)
        self.assertEqual(
            {(a, n) for a, targets in TRANSICOES_OS.items() for n in targets},
            VALID_TRANSITIONS,
        )

    def test_cancellation_requires_reason(self):
        for observacao in (None, "", "   "):
            with self.subTest(observacao=observacao), self.assertRaises(ValidationError) as context:
                TransicaoStatusOS(status_atual="ABERTA", status_novo="CANCELADA", observacao=observacao)
            self.assertIn("motivo", str(context.exception))

    def test_closed_order_cannot_be_reopened(self):
        with self.assertRaises(ValidationError) as context:
            TransicaoStatusOS(status_atual="CONCLUIDA", status_novo="ABERTA")
        self.assertIn("encerrada", str(context.exception))

    def test_detail_parses_timeline_and_legacy_rows(self):
        detalhe = OrdemServicoDetalhe.model_validate(DETAIL_RESPONSE)
        self.assertEqual(detalhe.historico[0].status_anterior, None)
        self.assertEqual(detalhe.historico[1].status_novo, "EM_ANDAMENTO")
        self.assertEqual(detalhe.data_abertura.year, 2026)
        legacy = OrdemServicoResumo.model_validate(
            {"id": 1, "status": "CONCLUIDA", "id_moto_cliente": 3}
        )
        self.assertIsNone(legacy.tipo_servico)
        self.assertIsNone(legacy.id_mecanico)


class MockedClientTestCase(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def make_client(self, handler):
        return XanoClient(token="jwt", transport=httpx.MockTransport(handler))


class OrdemServicoClientTests(MockedClientTestCase):
    def test_opening_sends_only_opening_fields(self):
        captured = {}

        def handler(request):
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            detalhe = client.abrir_ordem_servico(abertura(id_mecanico=None))

        self.assertEqual((captured["method"], captured["path"]), ("POST", "/api:test/ordens_servico"))
        self.assertEqual(
            set(captured["body"]),
            {"id_moto_cliente", "tipo_servico", "descricao_problema", "quilometragem"},
        )
        for forbidden in ("status", "id_funcionario", "id_cliente", "data_abertura", "id_mecanico"):
            self.assertNotIn(forbidden, captured["body"])
        self.assertIsInstance(detalhe, OrdemServicoDetalhe)

    def test_transition_posts_expected_and_new_status(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            client.transicionar_ordem_servico(
                31, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
            )

        self.assertEqual(captured["path"], "/api:test/ordens_servico/31/status")
        self.assertEqual(
            captured["body"],
            {"status_atual": "ABERTA", "status_novo": "EM_ANDAMENTO", "observacao": None},
        )

    def test_list_sends_only_given_filters(self):
        queries = []

        def handler(request):
            queries.append(dict(request.url.params))
            return httpx.Response(200, json=[DETAIL_RESPONSE])

        with self.make_client(handler) as client:
            client.list_ordens_servico()
            client.list_ordens_servico(status="ABERTA")
            ordens = client.list_ordens_servico(id_moto_cliente=12)

        self.assertEqual(queries, [{}, {"status": "ABERTA"}, {"id_moto_cliente": "12"}])
        self.assertEqual(ordens[0].nome_mecanico, "Bruno")

    def test_detail_and_mechanics_use_read_endpoints(self):
        paths = []

        def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith("mecanicos"):
                return httpx.Response(200, json=[{"id": 4, "nome_funcionario": "Bruno"}])
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            client.get_ordem_servico(31)
            mecanicos = client.list_mecanicos()

        self.assertEqual(paths, ["/api:test/ordens_servico/31", "/api:test/oficina/mecanicos"])
        self.assertEqual(mecanicos[0].nome_funcionario, "Bruno")

    def test_errors_are_typed(self):
        cases = {
            400: XanoValidationError,
            403: XanoPermissionError,
            404: XanoNotFoundError,
        }
        for status_code, error_type in cases.items():
            with self.subTest(status_code=status_code):
                def handler(request, status_code=status_code):
                    return httpx.Response(status_code, json={"message": "Transição de status inválida."})

                with self.make_client(handler) as client, self.assertRaises(error_type):
                    client.transicionar_ordem_servico(
                        31, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                    )


DETAIL_WITH_ITEMS = {
    **DETAIL_RESPONSE,
    "valor_pecas": 91.8,
    "valor_servicos": 380,
    "valor_total": 471.8,
    "itens": [
        {"id": 7, "id_os": 31, "tipo_item": "PECA", "id_produto": 3, "codigo": "OLEO20W50",
         "nome_produto": "Óleo 20W50", "quantidade": 2, "valor_unitario": 45.9,
         "valor_total_item": 91.8, "estoque_baixado": True, "created_at": 1790000700000},
        {"id": 8, "id_os": 31, "tipo_item": "SERVICO", "id_produto": None,
         "descricao": "Troca do kit de embreagem", "quantidade": 1, "valor_unitario": 380,
         "valor_total_item": 380, "estoque_baixado": False},
    ],
}


class ItemOSDtoTests(unittest.TestCase):
    def test_part_is_priced_by_xano(self):
        item = ItemOSCreate(
            tipo_item="PECA", id_produto=3, quantidade=2, valor_unitario="1.00", descricao="x"
        )
        self.assertEqual(
            item.model_dump(mode="json", exclude_none=True),
            {"tipo_item": "PECA", "id_produto": 3, "quantidade": 2},
        )

    def test_part_requires_product(self):
        with self.assertRaises(ValidationError) as context:
            ItemOSCreate(tipo_item="PECA", quantidade=1)
        self.assertIn("Selecione o produto.", str(context.exception))

    def test_service_requires_description_and_value(self):
        cases = {
            "Informe a descrição do serviço.": {"descricao": "   ", "valor_unitario": "10"},
            "Informe o valor do serviço.": {"descricao": "Revisão"},
        }
        for message, fields in cases.items():
            with self.subTest(message=message), self.assertRaises(ValidationError) as context:
                ItemOSCreate(tipo_item="SERVICO", quantidade=1, **fields)
            self.assertIn(message, str(context.exception))

    def test_service_ignores_product_and_strips_description(self):
        item = ItemOSCreate(
            tipo_item="SERVICO",
            id_produto=3,
            descricao="  Troca do kit  ",
            quantidade=1,
            valor_unitario=Decimal("380.00"),
        )
        self.assertIsNone(item.id_produto)
        self.assertEqual(item.descricao, "Troca do kit")

    def test_rejects_invalid_numbers(self):
        invalid = (
            {"tipo_item": "PECA", "id_produto": 3, "quantidade": 0},
            {"tipo_item": "PECA", "id_produto": 0, "quantidade": 1},
            {"tipo_item": "SERVICO", "descricao": "x", "quantidade": 1, "valor_unitario": "0"},
            {"tipo_item": "SERVICO", "descricao": "x", "quantidade": 1, "valor_unitario": "1.234"},
            {"tipo_item": "BRINDE", "quantidade": 1},
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                ItemOSCreate(**data)

    def test_detail_parses_items_totals_and_legacy_items(self):
        detalhe = OrdemServicoDetalhe.model_validate(DETAIL_WITH_ITEMS)
        self.assertEqual(detalhe.valor_total, Decimal("471.8"))
        self.assertEqual([item.tipo_item for item in detalhe.itens], ["PECA", "SERVICO"])
        self.assertTrue(detalhe.itens[0].estoque_baixado)
        self.assertIsNone(detalhe.itens[1].id_produto)
        legacy = ItemOrdemServico.model_validate(
            {"id": 1, "tipo_item": None, "id_produto": 2, "quantidade": 1, "valor_total_item": 10}
        )
        self.assertEqual(legacy.tipo_item, "PECA")
        self.assertIsNone(legacy.estoque_baixado)
        self.assertIsNone(legacy.valor_unitario)


class ItemOSClientTests(MockedClientTestCase):
    def test_add_item_posts_only_item_fields(self):
        captured = {}

        def handler(request):
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_WITH_ITEMS)

        with self.make_client(handler) as client:
            detalhe = client.adicionar_item_ordem_servico(
                31, ItemOSCreate(tipo_item="PECA", id_produto=3, quantidade=2)
            )

        self.assertEqual(
            (captured["method"], captured["path"]), ("POST", "/api:test/ordens_servico/31/itens")
        )
        self.assertEqual(captured["body"], {"tipo_item": "PECA", "id_produto": 3, "quantidade": 2})
        self.assertEqual(len(detalhe.itens), 2)

    def test_add_service_sends_value_as_text_decimal(self):
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_WITH_ITEMS)

        with self.make_client(handler) as client:
            client.adicionar_item_ordem_servico(
                31,
                ItemOSCreate(
                    tipo_item="SERVICO", descricao="Revisão", quantidade=1, valor_unitario="380"
                ),
            )

        self.assertEqual(
            captured["body"],
            {"tipo_item": "SERVICO", "descricao": "Revisão", "quantidade": 1, "valor_unitario": "380"},
        )

    def test_remove_item_deletes_nested_route_and_returns_detail(self):
        captured = {}

        def handler(request):
            captured["method"] = request.method
            captured["path"] = request.url.path
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            detalhe = client.remover_item_ordem_servico(31, 7)

        self.assertEqual(
            (captured["method"], captured["path"]),
            ("DELETE", "/api:test/ordens_servico/31/itens/7"),
        )
        self.assertIsInstance(detalhe, OrdemServicoDetalhe)

    def test_insufficient_balance_is_a_validation_error(self):
        message = "Saldo insuficiente para OLEO20W50: disponível 1, solicitado 2."

        def handler(request):
            return httpx.Response(400, json={"message": message})

        with self.make_client(handler) as client, self.assertRaises(XanoValidationError) as context:
            client.adicionar_item_ordem_servico(
                31, ItemOSCreate(tipo_item="PECA", id_produto=3, quantidade=2)
            )
        self.assertEqual(str(context.exception), message)


if __name__ == "__main__":
    unittest.main()
