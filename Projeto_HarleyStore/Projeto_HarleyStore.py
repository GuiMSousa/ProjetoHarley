"""Application entry point for the authenticated Reflex shell."""

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.cadastros_pages import cadastro_page
from Projeto_HarleyStore.cadastros_state import CadastrosState
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


def access_denied_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Acesso negado", size="7"),
            rx.callout(
                "Seu perfil não possui permissão para acessar esta área.",
                icon="lock",
                color_scheme="red",
            ),
            rx.link("Voltar para a visão geral", href="/"),
            align="center",
            spacing="4",
        ),
        min_height="70vh",
        padding="2rem",
    )


def protected_page(title: str, route: str) -> rx.Component:
    allowed = AuthState.can_manage if route == "/admin" else AuthState.can_workshop
    return rx.cond(
        AuthState.is_authenticated,
        rx.cond(
            allowed,
            app_shell(rx.heading(title, size="8", padding="2rem")),
            app_shell(access_denied_page()),
        ),
        login_page(),
    )


app = rx.App()
app.add_page(index, route="/", on_load=AuthState.restore_session)
app.add_page(login, route="/login")
app.add_page(
    lambda: protected_page("Administração", "/admin"),
    route="/admin",
    on_load=AuthState.restore_session,
)
app.add_page(
    lambda: protected_page("Oficina", "/workshop"),
    route="/workshop",
    on_load=AuthState.restore_session,
)
app.add_page(
    lambda: cadastro_page("clientes"),
    route="/cadastros/clientes",
    on_load=CadastrosState.load_clientes,
)
app.add_page(
    lambda: cadastro_page("motos_clientes"),
    route="/cadastros/motos-clientes",
    on_load=CadastrosState.load_motos_clientes,
)
app.add_page(
    lambda: cadastro_page("produtos"),
    route="/cadastros/produtos",
    on_load=CadastrosState.load_produtos,
)
app.add_page(
    lambda: cadastro_page("fornecedores"),
    route="/cadastros/fornecedores",
    on_load=CadastrosState.load_fornecedores,
)
app.add_page(
    lambda: cadastro_page("funcionarios"),
    route="/cadastros/funcionarios",
    on_load=CadastrosState.load_funcionarios,
)
