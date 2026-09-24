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
            rx.cond(AuthState.error_message != "", rx.text(AuthState.error_message, color=COLORS["danger"], size="2")),
            rx.button("Entrar", on_click=AuthState.login, width="100%", **PRIMARY_BUTTON),
            spacing="4",
            width="min(100%, 25rem)",
            padding="2rem",
            **PANEL,
        ),
        min_height="100vh",
        background=COLORS["black"],
        padding="1.5rem",
    )


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.text("HD / OPERATIONS", color=COLORS["orange"], font_weight="800"),
        rx.link("Visão geral", href="/", color=COLORS["text"]),
        rx.cond(AuthState.can_manage, rx.link("Administração", href="/admin", color=COLORS["text"])),
        rx.cond(AuthState.can_workshop, rx.link("Oficina", href="/workshop", color=COLORS["text"])),
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