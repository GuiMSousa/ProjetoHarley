"""Authentication state and session lifecycle for the Reflex app."""

from __future__ import annotations

import re

import reflex as rx

from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoPermissionError,
)


class AuthState(rx.State):
    auth_token: str = rx.Cookie(
        name="harley_auth_token",
        max_age=86400,
        secure=False,
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
            self.load_user()
            return rx.redirect("/")
        except XanoError as error:
            self.error_message = str(error)
            self.auth_token = ""
        finally:
            self.is_loading = False
        return None

    @rx.event
    def load_user(self) -> None:
        if not self.auth_token:
            self.is_authenticated = False
            return
        try:
            with XanoClient(token=self.auth_token) as client:
                response = client.current_user()
            user = response.get("user", response)
            employee = response.get("funcionario") or {}
            self.user_name = str(user.get("name", ""))
            self.employee_name = str(employee.get("nome_funcionario", ""))
            self.employee_role = str(employee.get("tipo", ""))
            self.is_authenticated = bool(self.employee_role)
            if not self.is_authenticated:
                self.error_message = "Usuário sem funcionário associado."
        except XanoAuthenticationError:
            self.logout()
        except XanoPermissionError:
            self.error_message = "Seu perfil não possui acesso a esta operação."
            self.is_authenticated = True
            return rx.toast(
                "Acesso negado para este perfil.",
                level="error",
                position="top-right",
            )
        except XanoError as error:
            self.error_message = str(error)
            self.is_authenticated = False

    @rx.event
    def restore_session(self) -> None:
        if self.auth_token:
            self.load_user()

    @rx.event
    def logout(self):
        self.auth_token = ""
        self.is_authenticated = False
        self.user_name = ""
        self.employee_name = ""
        self.employee_role = ""
        return rx.redirect("/login")