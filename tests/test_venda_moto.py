"""Change 9: sale DTO and the POST vender_moto request sent by the Python client."""

import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.motos import VendaMotoCreate, VendaMotoResultado
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoNotFoundError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoResponseError,
    XanoValidationError,
)


RESULTADO = {"id_transacao": 41, "id_moto_cliente": 87, "status": "SUCESSO"}


def venda(**overrides):
    data = {"id_moto": 9, "id_cliente": 5, "valor_venda": "185000.00"}
    data.update(overrides)
    return VendaMotoCreate(**data)


class VendaDtoTests(unittest.TestCase):
    def test_plate_is_optional_and_normalized(self):
        self.assertIsNone(venda().placa)
        self.assertIsNone(venda(placa="   ").placa)
        self.assertEqual(venda(placa=" abc-1d23 ").placa, "ABC1D23")
        self.assertEqual(venda(placa="abc 1234").placa, "ABC1234")

    def test_blank_note_is_absent(self):
        self.assertIsNone(venda(observacao="  ").observacao)
        self.assertEqual(venda(observacao=" À vista ").observacao, "À vista")

    def test_rejects_invalid_fields(self):
        invalid = (
            {"valor_venda": "0"},
            {"valor_venda": "-1"},
            {"valor_venda": "1.999"},
            {"valor_venda": "NaN"},
            {"id_cliente": 0},
            {"id_moto": 0},
            {"placa": "AB12345"},
            {"placa": "ABCD123"},
            {"placa": "ABC12345"},
            {"observacao": "x" * 501},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                venda(**overrides)

    def test_minimum_sale_value_is_one_cent(self):
        self.assertEqual(venda(valor_venda="0.01").valor_venda, Decimal("0.01"))

    def test_seller_is_never_part_of_the_body(self):
        self.assertNotIn("id_funcionario", VendaMotoCreate.model_fields)
        self.assertNotIn("id_funcionario", venda(id_funcionario=3).model_dump())


class VendaClientTests(unittest.TestCase):
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
            return response or httpx.Response(200, json=RESULTADO)

        return requests, handler

    def test_sale_posts_the_contract_fields_with_the_session_token(self):
        requests, handler = self.capture()
        with self.make_client(handler) as client:
            resultado = client.vender_moto(
                venda(valor_venda=Decimal("185000.5"), placa="abc-1d23", observacao="À vista")
            )

        (request,) = requests
        self.assertEqual((request.method, request.url.path), ("POST", "/api:harley/vender_moto"))
        self.assertEqual(request.headers["Authorization"], "Bearer jwt")
        self.assertEqual(
            json.loads(request.content),
            {
                "id_moto": 9,
                "id_cliente": 5,
                "valor_venda": "185000.5",
                "placa": "ABC1D23",
                "observacao": "À vista",
            },
        )
        self.assertEqual(resultado, VendaMotoResultado(**RESULTADO))

    def test_sale_without_plate_or_note_omits_them(self):
        requests, handler = self.capture()
        with self.make_client(handler) as client:
            client.vender_moto(venda(placa="", observacao=""))
        self.assertEqual(
            json.loads(requests[0].content),
            {"id_moto": 9, "id_cliente": 5, "valor_venda": "185000.00"},
        )

    def test_missing_session_fails_before_the_request(self):
        requests, handler = self.capture()
        with XanoClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(XanoAuthenticationError):
                client.vender_moto(venda())
        self.assertEqual(requests, [])

    def test_business_rejections_keep_the_xano_message(self):
        for message in (
            "Esta moto já foi vendida.",
            "Esta moto está reservada para outro cliente.",
            "A moto foi alterada por outro usuário. Atualize e tente novamente.",
            "Placa já cadastrada em uma moto de cliente.",
        ):
            _, handler = self.capture(httpx.Response(400, json={"message": message}))
            with self.subTest(message=message), self.make_client(handler) as client:
                with self.assertRaises(XanoValidationError) as context:
                    client.vender_moto(venda())
                self.assertEqual(str(context.exception), message)

    def test_status_errors_are_typed(self):
        for status_code, error_class in (
            (401, XanoAuthenticationError),
            (403, XanoPermissionError),
            (404, XanoNotFoundError),
            (429, XanoRateLimitError),
        ):
            _, handler = self.capture(httpx.Response(status_code, json={"message": "x"}))
            with self.subTest(status_code=status_code), self.make_client(handler) as client:
                with self.assertRaises(error_class):
                    client.vender_moto(venda())

    def test_unexpected_success_payload_is_a_response_error(self):
        _, handler = self.capture(httpx.Response(200, json={"status": "OK"}))
        with self.make_client(handler) as client, self.assertRaises(XanoResponseError):
            client.vender_moto(venda())


if __name__ == "__main__":
    unittest.main()
