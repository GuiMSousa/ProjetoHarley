import os
import unittest
from unittest.mock import patch

import httpx
from pydantic import TypeAdapter

from Projeto_HarleyStore.services.motos import Moto
from Projeto_HarleyStore.services.xano_client import (
    AuthTokenResponse,
    CurrentUserResponse,
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoPermissionError,
    XanoResponseError,
    XanoValidationError,
)


class XanoClientTests(unittest.TestCase):
    def setUp(self):
        self.xano_environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test"},
        )
        self.xano_environment.start()

    def tearDown(self):
        self.xano_environment.stop()

    def make_client(self, handler, token="token"):
        return XanoClient(
            token=token,
            transport=httpx.MockTransport(handler),
        )

    def test_authenticated_request_sends_bearer_header(self):
        def handler(request):
            self.assertEqual(request.headers["Authorization"], "Bearer token")
            return httpx.Response(200, json={"ok": True})

        with self.make_client(handler) as client:
            self.assertEqual(client.get("motos"), {"ok": True})

    def test_missing_token_fails_before_transport(self):
        with self.make_client(lambda request: httpx.Response(200), token=None) as client:
            with self.assertRaises(XanoAuthenticationError):
                client.get("motos")

    def test_status_errors_are_typed(self):
        error_types = {
            401: XanoAuthenticationError,
            403: XanoPermissionError,
            422: XanoValidationError,
        }
        for status_code, error_type in error_types.items():
            with self.subTest(status_code=status_code):
                def handler(request, status_code=status_code):
                    return httpx.Response(status_code, json={"message": "secret"})

                with self.make_client(handler) as client:
                    with self.assertRaises(error_type) as context:
                        client.get("motos")
                    self.assertNotIn("secret", str(context.exception))
                    self.assertNotIn("token", str(context.exception))

    def test_transport_error_is_typed_without_secret(self):
        def handler(request):
            raise httpx.ConnectError("connection failed", request=request)

        with self.make_client(handler) as client:
            with self.assertRaises(XanoError) as context:
                client.get("motos")
            self.assertNotIn("token", str(context.exception))

    def test_login_response_is_typed(self):
        def handler(request):
            self.assertFalse(request.headers.get("Authorization"))
            return httpx.Response(200, json={"authToken": "jwt", "user_id": 7})

        with self.make_client(handler, token=None) as client:
            response = client.login("user@example.com", "password")
        self.assertEqual(response, {"authToken": "jwt", "user_id": 7})

    def test_login_payload_requires_auth_token(self):
        def handler(request):
            return httpx.Response(200, json={"user_id": 7})

        with self.make_client(handler, token=None) as client:
            with self.assertRaises(XanoResponseError):
                client.login("user@example.com", "password")

    def test_current_user_response_is_typed_and_excludes_password(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "user": {
                        "id": 7,
                        "name": "Gerente",
                        "email": "manager@example.com",
                        "role": "member",
                        "id_funcionario": 3,
                        "password": "must-not-leak",
                    },
                    "funcionario": {
                        "id": 3,
                        "nome_funcionario": "Gerente",
                        "cargo": "Gestor",
                        "tipo": "GERENTE",
                    },
                },
            )

        with self.make_client(handler) as client:
            response = client.current_user()
        self.assertIsInstance(response, CurrentUserResponse)
        self.assertEqual(response.funcionario.tipo, "GERENTE")
        self.assertNotIn("password", response.user.model_dump())

    def test_generic_response_model_can_parse_lists(self):
        def handler(request):
            return httpx.Response(
                200,
                json=[{"id": 1, "marca": "Harley", "modelo": "Iron"}],
            )

        with self.make_client(handler) as client:
            motos = client.get("motos", response_model=TypeAdapter(list[Moto]))
        self.assertEqual(motos[0].id, 1)


if __name__ == "__main__":
    unittest.main()
