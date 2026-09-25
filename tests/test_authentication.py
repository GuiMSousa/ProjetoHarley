import os
import unittest
from unittest.mock import MagicMock, patch

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.services.xano_client import (
    CurrentUserResponse,
    XanoAuthenticationError,
    XanoEmployee,
    XanoPermissionError,
    XanoUser,
)
from Projeto_HarleyStore.xano_config import (
    XanoConfigurationError,
    xano_auth_cookie_secure,
)


class AuthenticationTests(unittest.TestCase):
    def make_state(self):
        state = object.__new__(AuthState)
        object.__setattr__(state, "dirty_vars", set())
        object.__setattr__(state, "substates", {})
        state.auth_token = "token"
        state.is_authenticated = False
        state.error_message = ""
        return state

    def make_user_response(self, role="GERENTE"):
        return CurrentUserResponse(
            user=XanoUser(id=1, name="Gerente", email="manager@example.com"),
            funcionario=XanoEmployee(
                id=2,
                nome_funcionario="Gerente",
                cargo="Gestor",
                tipo=role,
            ),
        )

    def run_load_user(self, state):
        with patch.object(AuthState, "_mark_dirty", lambda instance: None):
            return state._load_user()

    def test_load_user_authenticates_only_after_validating_employee(self):
        state = self.make_state()
        client = MagicMock()
        client.current_user.return_value = self.make_user_response()
        client.__enter__.return_value = client
        with patch("Projeto_HarleyStore.auth.XanoClient", return_value=client):
            self.assertTrue(self.run_load_user(state))
        self.assertTrue(state.is_authenticated)
        self.assertEqual(state.employee_role, "GERENTE")

    def test_load_user_clears_session_after_401(self):
        state = self.make_state()
        client = MagicMock()
        client.current_user.side_effect = XanoAuthenticationError("expired")
        client.__enter__.return_value = client
        with patch("Projeto_HarleyStore.auth.XanoClient", return_value=client):
            self.assertFalse(self.run_load_user(state))
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.auth_token, "")
        self.assertIn("expirou", state.error_message)

    def test_load_user_preserves_token_after_403(self):
        state = self.make_state()
        client = MagicMock()
        client.current_user.side_effect = XanoPermissionError("forbidden")
        client.__enter__.return_value = client
        with patch("Projeto_HarleyStore.auth.XanoClient", return_value=client):
            self.assertFalse(self.run_load_user(state))
        self.assertEqual(state.auth_token, "token")
        self.assertFalse(state.is_authenticated)
        self.assertIn("acesso", state.error_message)

    def test_load_user_rejects_unlinked_employee(self):
        state = self.make_state()
        client = MagicMock()
        client.current_user.return_value = CurrentUserResponse(
            user=XanoUser(id=1, name="Sem vínculo"), funcionario=None
        )
        client.__enter__.return_value = client
        with patch("Projeto_HarleyStore.auth.XanoClient", return_value=client):
            self.assertFalse(self.run_load_user(state))
        self.assertFalse(state.is_authenticated)
        self.assertIn("vinculado", state.error_message)

    def test_load_user_rejects_inactive_employee(self):
        state = self.make_state()
        response = self.make_user_response()
        response.funcionario.ativo = False
        client = MagicMock()
        client.current_user.return_value = response
        client.__enter__.return_value = client
        with patch("Projeto_HarleyStore.auth.XanoClient", return_value=client):
            self.assertFalse(self.run_load_user(state))
        self.assertFalse(state.is_authenticated)
        self.assertIn("inativo", state.error_message)

    def test_clearing_session_resets_page_states(self):
        from reflex.state import State

        from Projeto_HarleyStore.cadastros_state import CadastrosState
        from Projeto_HarleyStore.entradas_state import EntradasState

        root = State(_reflex_internal_init=True)
        cadastros = root.get_substate(CadastrosState.get_full_name().split("."))
        entradas = root.get_substate(EntradasState.get_full_name().split("."))
        cadastros.clientes = [{"id": "1", "primary": "Cliente anterior"}]
        entradas.entradas = [{"id": "7", "documento": "NF-1"}]
        entradas.auth_token = "token"
        entradas.is_authenticated = True

        response = entradas._xano_error_response(XanoAuthenticationError("expired"))

        self.assertEqual(cadastros.clientes, [])
        self.assertEqual(entradas.entradas, [])
        self.assertEqual(entradas.auth_token, "")
        self.assertFalse(entradas.is_authenticated)
        self.assertIn("sessão", entradas.error_message)
        self.assertIsNotNone(response)

    def test_cookie_secure_setting_accepts_explicit_boolean_values(self):
        for value, expected in {
            "false": False,
            "0": False,
            "true": True,
            "1": True,
        }.items():
            with self.subTest(value=value), patch.dict(
                os.environ, {"XANO_AUTH_COOKIE_SECURE": value}
            ):
                self.assertEqual(xano_auth_cookie_secure(), expected)

    def test_cookie_secure_setting_rejects_ambiguous_values(self):
        with patch.dict(os.environ, {"XANO_AUTH_COOKIE_SECURE": "sometimes"}):
            with self.assertRaises(XanoConfigurationError):
                xano_auth_cookie_secure()

    def test_route_guards_match_domain_roles(self):
        self.assertTrue(role_allows_route("GERENTE", "/admin"))
        self.assertFalse(role_allows_route("VENDEDOR", "/admin"))
        self.assertFalse(role_allows_route("MECANICO", "/admin"))
        self.assertTrue(role_allows_route("GERENTE", "/workshop"))
        self.assertTrue(role_allows_route("MECANICO", "/workshop"))
        self.assertFalse(role_allows_route("VENDEDOR", "/workshop"))

    def test_route_matrix_covers_registrations_and_stock(self):
        expected = {
            "/cadastros/clientes": {"GERENTE", "VENDEDOR", "MECANICO"},
            "/cadastros/motos-clientes": {"GERENTE", "VENDEDOR", "MECANICO"},
            "/cadastros/produtos": {"GERENTE", "VENDEDOR", "MECANICO"},
            "/cadastros/fornecedores": {"GERENTE"},
            "/cadastros/funcionarios": {"GERENTE"},
            "/estoque/entradas": {"GERENTE", "VENDEDOR", "MECANICO"},
        }
        for route, roles in expected.items():
            for role in ("GERENTE", "VENDEDOR", "MECANICO"):
                with self.subTest(route=route, role=role):
                    self.assertEqual(role_allows_route(role, route), role in roles)

    def test_unknown_route_or_role_is_denied(self):
        self.assertFalse(role_allows_route("GERENTE", "/desconhecida"))
        self.assertFalse(role_allows_route("", "/cadastros/clientes"))

    def test_allowed_routes_follow_session_and_role(self):
        vendor = type(
            "Fixture", (), {"is_authenticated": True, "employee_role": "VENDEDOR"}
        )()
        routes = AuthState.allowed_routes.fget(vendor)
        self.assertIn("/cadastros/produtos", routes)
        self.assertIn("/estoque/entradas", routes)
        self.assertNotIn("/cadastros/fornecedores", routes)
        anonymous = type(
            "Fixture", (), {"is_authenticated": False, "employee_role": "GERENTE"}
        )()
        self.assertEqual(AuthState.allowed_routes.fget(anonymous), [])

    def test_successful_session_restore_emits_no_toast(self):
        state = self.make_state()
        client = MagicMock()
        client.current_user.return_value = self.make_user_response()
        with patch("Projeto_HarleyStore.auth.XanoClient") as client_class, patch.object(
            AuthState, "_mark_dirty", lambda instance: None
        ):
            client_class.return_value.__enter__.return_value = client
            result = AuthState.load_user.fn(state)
        self.assertIsNone(result)
        self.assertTrue(state.is_authenticated)


if __name__ == "__main__":
    unittest.main()
