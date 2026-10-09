"""Change 11: counter sale DTOs and the POST balcao/vendas request sent by the Python client."""

import json
import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.balcao import (
    MAX_ITENS_VENDA,
    VendaBalcaoCreate,
    VendaBalcaoDetalhe,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoPermissionError,
    XanoRateLimitError,
    XanoResponseError,
    XanoValidationError,
)


CHAVE = "3f2c9a4e-7b1d-4c8e-9f0a-2d6b5e8c1a7f"
RECIBO = {
    "id_transacao": 128,
    "tipo_transacao": "BALCAO",
    "data_transacao": 1791990000000,
    "valor_total": 389.7,
    "id_cliente": 14,
    "nome_cliente": "Ana Souza",
    "id_funcionario": 3,
    "nome_funcionario": "Carlos Vendedor",
    "itens": [
        {
            "id": 1,
            "id_transacao": 128,
            "id_produto": 7,
            "codigo": "FLT0001",
            "nome_produto": "Filtro de óleo",
            "quantidade": 2,
            "valor_unitario": 89.9,
            "valor_total_item": 179.8,
            "chave_venda": CHAVE,
        },
        {
            "id": 2,
            "id_transacao": 128,
            "id_produto": 12,
            "codigo": "PST0102",
            "nome_produto": "Pastilha de freio",
            "quantidade": 1,
            "valor_unitario": 209.9,
            "valor_total_item": 209.9,
            "chave_venda": CHAVE,
        },
    ],
}


def venda(**overrides):
    data = {
        "chave_venda": CHAVE,
        "id_cliente": 14,
        "total_esperado": "389.70",
        "itens": [{"id_produto": 7, "quantidade": 2}, {"id_produto": 12, "quantidade": 1}],
    }
    data.update(overrides)
    return VendaBalcaoCreate(**data)


class VendaBalcaoDtoTests(unittest.TestCase):
    def test_customer_is_optional(self):
        self.assertIsNone(venda(id_cliente=None).id_cliente)
        self.assertEqual(venda().id_cliente, 14)

    def test_rejects_invalid_payloads(self):
        muitos = [{"id_produto": n, "quantidade": 1} for n in range(1, MAX_ITENS_VENDA + 2)]
        invalid = (
            {"itens": []},
            {"itens": muitos},
            {"itens": [{"id_produto": 7, "quantidade": 1}, {"id_produto": 7, "quantidade": 2}]},
            {"itens": [{"id_produto": 7, "quantidade": 0}]},
            {"itens": [{"id_produto": 0, "quantidade": 1}]},
            {"total_esperado": "0"},
            {"total_esperado": "-1"},
            {"total_esperado": "10.005"},
            {"chave_venda": ""},
            {"chave_venda": "   "},
            {"chave_venda": "x" * 65},
            {"id_cliente": 0},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                venda(**overrides)

    def test_thirty_items_are_accepted(self):
        trinta = [{"id_produto": n, "quantidade": 1} for n in range(1, MAX_ITENS_VENDA + 1)]
        self.assertEqual(len(venda(itens=trinta).itens), 30)

    def test_repeated_product_message_is_readable(self):
        with self.assertRaises(ValidationError) as context:
            venda(itens=[{"id_produto": 7, "quantidade": 1}, {"id_produto": 7, "quantidade": 1}])
        self.assertIn("Um mesmo produto não pode aparecer mais de uma vez na venda.", str(context.exception))

    def test_price_seller_and_totals_are_never_part_of_the_body(self):
        for field in ("id_funcionario", "valor_unitario", "valor_total", "tipo_transacao"):
            with self.subTest(field=field):
                self.assertNotIn(field, VendaBalcaoCreate.model_fields)
        self.assertNotIn("valor_unitario", venda(itens=[{"id_produto": 7, "quantidade": 1, "valor_unitario": "1"}]).model_dump()["itens"][0])

    def test_receipt_parses_names_items_and_the_final_consumer(self):
        detalhe = VendaBalcaoDetalhe(**RECIBO)
        self.assertEqual(detalhe.id_transacao, 128)
        self.assertEqual(detalhe.valor_total, Decimal("389.7"))
        # Xano sends milliseconds since the epoch.
        self.assertEqual(detalhe.data_transacao, datetime.fromtimestamp(1791990000, tz=timezone.utc))
        self.assertEqual([item.codigo for item in detalhe.itens], ["FLT0001", "PST0102"])
        self.assertEqual(detalhe.itens[0].valor_total_item, Decimal("179.8"))
        anonimo = VendaBalcaoDetalhe(**{**RECIBO, "id_cliente": None, "nome_cliente": None})
        self.assertIsNone(anonimo.id_cliente)


class VendaBalcaoClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:harley", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def make_client(self, handler, token="jwt"):
        return XanoClient(token=token, transport=httpx.MockTransport(handler))

    def capture(self, response=None):
        requests = []

        def handler(request):
            requests.append(request)
            return response or httpx.Response(200, json=RECIBO)

        return requests, handler

    def test_sale_posts_the_cart_with_the_session_token(self):
        requests, handler = self.capture()
        with self.make_client(handler) as client:
            recibo = client.vender_balcao(venda())

        (request,) = requests
        self.assertEqual((request.method, request.url.path), ("POST", "/api:harley/balcao/vendas"))
        self.assertEqual(request.headers["Authorization"], "Bearer jwt")
        self.assertEqual(
            json.loads(request.content),
            {
                "chave_venda": CHAVE,
                "id_cliente": 14,
                "total_esperado": "389.70",
                "itens": [{"id_produto": 7, "quantidade": 2}, {"id_produto": 12, "quantidade": 1}],
            },
        )
        self.assertEqual(recibo.id_transacao, 128)

    def test_final_consumer_sale_omits_the_customer(self):
        requests, handler = self.capture()
        with self.make_client(handler) as client:
            client.vender_balcao(venda(id_cliente=None))
        self.assertNotIn("id_cliente", json.loads(requests[0].content))

    def test_missing_session_fails_before_the_request(self):
        requests, handler = self.capture()
        with XanoClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(XanoAuthenticationError):
                client.vender_balcao(venda())
        self.assertEqual(requests, [])

    def test_business_rejections_keep_the_xano_message(self):
        for message in (
            "Saldo insuficiente para FLT0001: disponível 3, solicitado 5.",
            "Os preços mudaram desde que o carrinho foi montado: o total agora é R$ 399,70. Revise o carrinho.",
            "A venda não foi registrada: o estoque ou os preços mudaram durante o fechamento. "
            "Revise o carrinho e tente novamente.",
        ):
            _, handler = self.capture(httpx.Response(400, json={"message": message}))
            with self.subTest(message=message), self.make_client(handler) as client:
                with self.assertRaises(XanoValidationError) as context:
                    client.vender_balcao(venda())
                self.assertEqual(str(context.exception), message)

    def test_status_errors_are_typed(self):
        for status_code, error_class in (
            (401, XanoAuthenticationError),
            (403, XanoPermissionError),
            (429, XanoRateLimitError),
        ):
            _, handler = self.capture(httpx.Response(status_code, json={"message": "x"}))
            with self.subTest(status_code=status_code), self.make_client(handler) as client:
                with self.assertRaises(error_class):
                    client.vender_balcao(venda())

    def test_unexpected_success_payload_is_a_response_error(self):
        _, handler = self.capture(httpx.Response(200, json={"status": "OK"}))
        with self.make_client(handler) as client, self.assertRaises(XanoResponseError):
            client.vender_balcao(venda())


if __name__ == "__main__":
    unittest.main()
