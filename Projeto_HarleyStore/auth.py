"""Authentication state and session lifecycle for the Reflex app."""

from __future__ import annotations

import re

import reflex as rx

from Projeto_HarleyStore.services.xano_client import (
    CurrentUserResponse,
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoPermissionError,
)
from Projeto_HarleyStore.xano_config import xano_auth_cookie_secure


def role_allows_route(role: str, route: str) -> bool:
    """Return whether a domain employee role may enter a protected route."""
    allowed_roles = {
        "/admin": {"GERENTE"},
        "/workshop": {"GERENTE", "MECANICO"},
    }
    return role in allowed_roles.get(route, set())


class AuthState(rx.State):
    auth_token: str = rx.Cookie(
        name="harley_auth_token",
        max_age=86400,
        secure=xano_auth_cookie_secure(),
        same_site="lax",
    )
    email: str = ""
    password: str = ""
    error_message: str = ""
    is_loading: bool = False
    is_authenticated: bool = False
    user_name: str = ""
    employee_name: str = ""
    employee_role: str = ""

    @rx.var
    def display_name(self) -> str:
        return self.employee_name or self.user_name or "Usuário"

    @rx.var
    def can_manage(self) -> bool:
        return self.employee_role == "GERENTE"

    @rx.var
    def can_workshop(self) -> bool:
        return self.employee_role in {"GERENTE", "MECANICO"}

    @rx.event
    def set_email(self, value: str) -> None:
        self.email = value.strip()
        self.error_message = ""

    @rx.event
    def set_password(self, value: str) -> None:
        self.password = value
        self.error_message = ""

    def _clear_session(self) -> None:
        self.auth_token = ""
        self.is_authenticated = False
        self.user_name = ""
        self.employee_name = ""
        self.employee_role = ""

    def _load_user(self) -> bool:
        if not self.auth_token:
            self.is_authenticated = False
            return False
        try:
            with XanoClient(token=self.auth_token) as client:
                response: CurrentUserResponse = client.current_user()
            employee = response.funcionario
            if employee is None:
                self.error_message = (
                    "Seu usuário ainda não está vinculado a um funcionário."
                )
                self.is_authenticated = False
                return False
            self.user_name = response.user.name or ""
            self.employee_name = employee.nome_funcionario
            self.employee_role = employee.tipo
            self.is_authenticated = employee.tipo in {
                "GERENTE",
                "VENDEDOR",
                "MECANICO",
            }
            if not self.is_authenticated:
                self.error_message = "Seu funcionário não possui um tipo válido."
            return self.is_authenticated
        except XanoAuthenticationError:
            self._clear_session()
            self.error_message = "Sua sessão expirou. Entre novamente."
        except XanoPermissionError:
            self.is_authenticated = False
            self.error_message = "Seu perfil não possui acesso a esta operação."
        except XanoError:
            self.is_authenticated = False
            self.error_message = "Não foi possível validar sua sessão no Xano."
        return False

    @rx.event
    def login(self):
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            self.error_message = "Informe um email válido."
            return None
        if len(self.password) < 8:
            self.error_message = "A senha deve ter pelo menos 8 caracteres."
            return None

        self.is_loading = True
        try:
            with XanoClient() as client:
                response = client.login(self.email, self.password)
            self.auth_token = str(response.get("authToken", ""))
            if not self.auth_token:
                raise XanoAuthenticationError("O Xano não retornou um token válido.")
            if self._load_user():
                self.password = ""
                return rx.redirect("/")
            return rx.toast(
                self.error_message,
                level="error",
                position="top-right",
            )
        except XanoError as error:
            self.error_message = str(error)
            self._clear_session()
            return rx.toast(
                self.error_message,
                level="error",
                position="top-right",
            )
        finally:
            self.is_loading = False

    @rx.event
    def load_user(self) -> None:
        if not self._load_user() and not self.auth_token:
            return rx.redirect("/login")
        return rx.toast(
            self.error_message,
            level="error",
            position="top-right",
        )

    @rx.event
    def restore_session(self) -> None:
        if self.auth_token:
            return self.load_user()

    @rx.event
    def logout(self):
        self._clear_session()
        return rx.redirect("/login")