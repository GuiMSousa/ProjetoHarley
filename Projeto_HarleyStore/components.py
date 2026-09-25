"""Reusable login and authenticated shell components."""

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.styles.theme import COLORS, PANEL, PRIMARY_BUTTON


def login_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.text("HARLEY-DAVIDSON", color=COLORS["orange"], font_weight="800", letter_spacing="0.14em"),
            rx.heading("Acesso ao sistema", size="7", color=COLORS["text"]),
            rx.text("Entre com seu usuário corporativo.", color=COLORS["muted"]),
            rx.input(placeholder="Email", type="email", value=AuthState.email, on_change=AuthState.set_email, width="100%"),
            rx.input(placeholder="Senha", type="password", value=AuthState.password, on_change=AuthState.set_password, width="100%"),
            rx.cond(
                AuthState.error_message != "",
                rx.callout(
                    AuthState.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
            ),
            rx.button(
                rx.cond(AuthState.is_loading, "Validando...", "Entrar"),
                on_click=AuthState.login,
                disabled=AuthState.is_loading,
                width="100%",
                **PRIMARY_BUTTON,
            ),
            spacing="4",
            width="min(100%, 25rem)",
            padding="2rem",
            **PANEL,
        ),
        min_height="100vh",
        background=COLORS["black"],
        padding="1.5rem",
    )


def nav_link(label: str, route: str) -> rx.Component:
    return rx.cond(
        AuthState.allowed_routes.contains(route),
        rx.link(label, href=route, color=COLORS["text"]),
    )


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.text("HD / OPERATIONS", color=COLORS["orange"], font_weight="800"),
        rx.link("Visão geral", href="/", color=COLORS["text"]),
        nav_link("Clientes", "/cadastros/clientes"),
        nav_link("Motos de clientes", "/cadastros/motos-clientes"),
        nav_link("Produtos e peças", "/cadastros/produtos"),
        nav_link("Entradas de mercadoria", "/estoque/entradas"),
        nav_link("Administração", "/admin"),
        nav_link("Fornecedores", "/cadastros/fornecedores"),
        nav_link("Funcionários", "/cadastros/funcionarios"),
        nav_link("Oficina", "/workshop"),
        spacing="4",
        align="stretch",
        padding="1.5rem",
        width="16rem",
        min_height="100vh",
        background=COLORS["graphite"],
        border_right=f"1px solid {COLORS['border']}",
    )


def app_shell(content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Painel de operações", size="6"),
                    rx.text(AuthState.employee_role, color=COLORS["orange"], size="2"),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.text(AuthState.display_name, color=COLORS["muted"]),
                rx.button("Sair", on_click=AuthState.logout, variant="outline"),
                width="100%",
                padding="1.25rem 1.5rem",
                border_bottom=f"1px solid {COLORS['border']}",
            ),
            content,
            align="stretch",
            width="100%",
            min_height="100vh",
            background=COLORS["black"],
        ),
        align="start",
        spacing="0",
        width="100%",
        min_height="100vh",
        background=COLORS["black"],
    )


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


def guarded_page(content: rx.Component, route: str) -> rx.Component:
    """Render content only for an authenticated role allowed on the route."""
    return rx.cond(
        AuthState.is_authenticated,
        rx.cond(
            AuthState.allowed_routes.contains(route),
            app_shell(content),
            app_shell(access_denied_page()),
        ),
        login_page(),
    )


def modal_panel(*children: rx.Component, width: str = "min(100%, 34rem)") -> rx.Component:
    """Centered overlay panel shared by forms and detail views."""
    return rx.box(
        rx.box(
            rx.vstack(
                *children,
                align="stretch",
                spacing="4",
                width=width,
                max_height="90vh",
                overflow_y="auto",
                padding="1.5rem",
                **PANEL,
            ),
            position="relative",
        ),
        position="fixed",
        inset="0",
        z_index="20",
        display="flex",
        align_items="center",
        justify_content="center",
        padding="1rem",
        background="rgba(0, 0, 0, 0.78)",
    )