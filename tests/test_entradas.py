import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.entradas import (
    EntradaMercadoriaCreate,
    EntradaMercadoriaDetalhe,
    EntradaMercadoriaResumo,
    ItemEntradaCreate,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoClient,
    XanoPermissionError,
    XanoValidationError,
)


def valid_payload(**overrides):
    data = {
        "id_fornecedor": 3,
        "numero_documento": "NF-1",
        "itens": [
            {"id_produto": 10, "quantidade": 5, "valor_unitario": Decimal("10.00")},
            {"id_produto": 11, "quantidade": 2, "valor_unitario": Decimal("25.50")},
        ],
    }
    data.update(overrides)
    return data


DETAIL_RESPONSE = {
    "id": 7,
    "id_fornecedor": 3,
    "numero_documento": "NF-1",
    "data_entrada": 1790000000000,
    "valor_total": 101.0,
    "nome_fornecedor": "Moto Parts",
    "id_funcionario": 1,
    "nome_funcionario": "Ana",
    "quantidade_itens": 2,
    "itens": [
        {
            "id": 20,
            "id_entrada": 7,
            "id_produto": 10,
            "codigo": "PX100",
            "nome_produto": "Pastilha",
            "quantidade": 5,
            "valor_unitario": 10.0,
            "valor_total_item": 50.0,
        },
        {
            "id": 21,
            "id_entrada": 7,
            "id_produto": 11,
            "codigo": "FL200",
            "nome_produto": "Filtro",
            "quantidade": 2,
            "valor_unitario": 25.5,
        },
    ],
}


class EntradaDtoTests(unittest.TestCase):
    def test_valid_payload_is_accepted(self):
        entrada = EntradaMercadoriaCreate(**valid_payload(numero_documento="  NF-1  "))
        self.assertEqual(entrada.numero_documento, "NF-1")
        self.assertEqual(len(entrada.itens), 2)

    def test_quantity_must_be_positive(self):
        for quantidade in (0, -1):
            with self.subTest(quantidade=quantidade), self.assertRaises(ValidationError):
                ItemEntradaCreate(id_produto=1, quantidade=quantidade, valor_unitario=Decimal("1"))

    def test_cost_price_must_be_positive(self):
        for valor in (Decimal("0"), Decimal("-0.01")):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                ItemEntradaCreate(id_produto=1, quantidade=1, valor_unitario=valor)

    def test_receipt_requires_items(self):
        with self.assertRaises(ValidationError):
            EntradaMercadoriaCreate(**valid_payload(itens=[]))

    def test_receipt_rejects_repeated_products(self):
        itens = [
            {"id_produto": 10, "quantidade": 1, "valor_unitario": Decimal("1")},
            {"id_produto": 10, "quantidade": 2, "valor_unitario": Decimal("2")},
        ]
        with self.assertRaises(ValidationError) as context:
            EntradaMercadoriaCreate(**valid_payload(itens=itens))
        self.assertIn("mesmo produto", str(context.exception))

    def test_receipt_requires_document_and_supplier(self):
        with self.assertRaises(ValidationError):
            EntradaMercadoriaCreate(**valid_payload(numero_documento="   "))
        with self.assertRaises(ValidationError):
            EntradaMercadoriaCreate(**valid_payload(id_fornecedor=0))

    def test_summary_accepts_legacy_records_without_document_or_author(self):
        resumo = EntradaMercadoriaResumo(
            id=1,
            id_fornecedor=2,
            numero_documento=None,
            id_funcionario=None,
            valor_total=None,
        )
        self.assertIsNone(resumo.numero_documento)
        self.assertEqual(resumo.quantidade_itens, 0)

    def test_detail_parses_items_and_fills_missing_item_total(self):
        detalhe = EntradaMercadoriaDetalhe.model_validate(DETAIL_RESPONSE)
        self.assertEqual(detalhe.data_entrada.year, 2026)
        self.assertEqual(detalhe.itens[0].valor_total_item, Decimal("50.0"))
        self.assertEqual(detalhe.itens[1].valor_total_item, Decimal("51.0"))


class EntradaClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test"},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def make_client(self, handler):
        return XanoClient(token="jwt", transport=httpx.MockTransport(handler))

    def test_register_sends_only_header_and_items(self):
        captured = {}

        def handler(request):
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            detalhe = client.registrar_entrada(EntradaMercadoriaCreate(**valid_payload()))

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["path"], "/api:test/entrada_mercadoria")
        self.assertEqual(
            set(captured["body"]), {"id_fornecedor", "numero_documento", "itens"}
        )
        for forbidden in ("id_funcionario", "valor_total", "data_entrada"):
            self.assertNotIn(forbidden, captured["body"])
        self.assertEqual(
            set(captured["body"]["itens"][0]),
            {"id_produto", "quantidade", "valor_unitario"},
        )
        self.assertIsInstance(detalhe, EntradaMercadoriaDetalhe)
        self.assertEqual(detalhe.valor_total, Decimal("101.0"))

    def test_list_and_detail_use_read_endpoints(self):
        requests = []

        def handler(request):
            requests.append((request.method, request.url.path))
            if request.url.path.endswith("/7"):
                return httpx.Response(200, json=DETAIL_RESPONSE)
            summary = {key: value for key, value in DETAIL_RESPONSE.items() if key != "itens"}
            return httpx.Response(200, json=[summary])

        with self.make_client(handler) as client:
            entradas = client.list_entradas()
            detalhe = client.get_entrada(7)

        self.assertEqual(entradas[0].nome_fornecedor, "Moto Parts")
        self.assertEqual(len(detalhe.itens), 2)
        self.assertEqual(
            requests,
            [
                ("GET", "/api:test/entrada_mercadoria"),
                ("GET", "/api:test/entrada_mercadoria/7"),
            ],
        )

    def test_business_rejection_becomes_readable_validation_error(self):
        def handler(request):
            return httpx.Response(
                400,
                json={"code": "ERROR_CODE_INPUT_ERROR", "message": "Fornecedor inativo ou inexistente."},
            )

        with self.make_client(handler) as client:
            with self.assertRaises(XanoValidationError) as context:
                client.registrar_entrada(EntradaMercadoriaCreate(**valid_payload()))
        self.assertEqual(str(context.exception), "Fornecedor inativo ou inexistente.")

    def test_non_manager_registration_is_a_permission_error(self):
        with self.make_client(lambda request: httpx.Response(403, json={})) as client:
            with self.assertRaises(XanoPermissionError):
                client.registrar_entrada(EntradaMercadoriaCreate(**valid_payload()))


if __name__ == "__main__":
    unittest.main()
