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


if __name__ == "__main__":
    unittest.main()
