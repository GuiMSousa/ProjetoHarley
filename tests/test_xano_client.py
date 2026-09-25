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
    XanoNotFoundError,
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
            500: XanoError,
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

    def test_auth_and_business_endpoints_use_their_own_api_groups(self):
        requested = []

        def handler(request):
            requested.append(str(request.url))
            if request.url.path.endswith("auth/login"):
                return httpx.Response(200, json={"authToken": "jwt"})
            if request.url.path.endswith("auth/me"):
                return httpx.Response(200, json={"user": {"id": 1}})
            return httpx.Response(200, json=[])

        with patch.dict(
            os.environ,
            {"XANO_AUTH_API_BASE_URL": "https://xano.test/api:auth/"},
        ):
            with self.make_client(handler) as client:
                client.login("user@example.com", "password")
                client.current_user()
                client.list_clientes()

        self.assertEqual(
            requested,
            [
                "https://xano.test/api:auth/auth/login",
                "https://xano.test/api:auth/auth/me",
                "https://xano.test/api:test/clientes",
            ],
        )

    def test_auth_group_falls_back_to_business_base_url(self):
        requested = []

        def handler(request):
            requested.append(str(request.url))
            return httpx.Response(200, json={"authToken": "jwt"})

        with patch.dict(os.environ, {"XANO_AUTH_API_BASE_URL": ""}):
            with self.make_client(handler, token=None) as client:
                client.login("user@example.com", "password")
        self.assertEqual(requested, ["https://xano.test/api:test/auth/login"])

    def test_missing_resource_is_a_typed_not_found_error(self):
        with self.make_client(
            lambda request: httpx.Response(404, json={"message": "secret"})
        ) as client:
            with self.assertRaises(XanoNotFoundError) as context:
                client.get("entrada_mercadoria/999")
        self.assertNotIn("secret", str(context.exception))
        self.assertEqual(context.exception.status_code, 404)

    def test_linked_employee_defaults_to_active_and_reads_flag(self):
        payload = {
            "user": {"id": 1},
            "funcionario": {"id": 2, "nome_funcionario": "Ana", "tipo": "GERENTE"},
        }
        self.assertTrue(CurrentUserResponse.model_validate(payload).funcionario.ativo)
        payload["funcionario"]["ativo"] = False
        self.assertFalse(CurrentUserResponse.model_validate(payload).funcionario.ativo)

    def test_validation_errors_expose_only_short_business_message(self):
        for status_code in (400, 422):
            with self.subTest(status_code=status_code):
                def handler(request, status_code=status_code):
                    return httpx.Response(
                        status_code,
                        json={"code": "ERROR_CODE_INPUT_ERROR", "message": "Fornecedor inativo."},
                    )

                with self.make_client(handler) as client:
                    with self.assertRaises(XanoValidationError) as context:
                        client.get("motos")
                self.assertEqual(str(context.exception), "Fornecedor inativo.")
                self.assertEqual(context.exception.status_code, status_code)

    def test_validation_error_without_readable_message_stays_generic(self):
        payloads = [
            {"message": "x" * 201},
            {"message": {"nested": "value"}},
            ["not", "an", "object"],
        ]
        for payload in payloads:
            with self.subTest(payload=str(payload)[:20]):
                def handler(request, payload=payload):
                    return httpx.Response(400, json=payload)

                with self.make_client(handler) as client:
                    with self.assertRaises(XanoValidationError) as context:
                        client.get("motos")
                self.assertEqual(str(context.exception), "Xano rejected the request data.")

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
