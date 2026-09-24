"""Application entry point for the authenticated Reflex shell."""

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.components import app_shell, login_page


def dashboard() -> rx.Component:
    return rx.vstack(
        rx.heading("Bem-vindo à operação", size="8"),
        rx.text(
            "A base autenticada está pronta para receber as próximas fatias funcionais.",
            color="#a7a7a7",
        ),
        padding="2rem",
        align="start",
    )


def index() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        app_shell(dashboard()),
        login_page(),
    )


def login() -> rx.Component:
    return login_page()


def protected_page(title: str) -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        app_shell(rx.heading(title, size="8", padding="2rem")),
        login_page(),
    )


app = rx.App()
app.add_page(index, route="/", on_load=AuthState.restore_session)
app.add_page(login, route="/login")
app.add_page(lambda: protected_page("Administração"), route="/admin")
app.add_page(lambda: protected_page("Oficina"), route="/workshop")
