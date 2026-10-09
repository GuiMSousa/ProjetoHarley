"""Overview page: shortcuts to the areas the signed-in role may enter (no metrics)."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.components import PUBLIC_ROUTES, page_body
from Projeto_HarleyStore.styles.theme import COLORS
from Projeto_HarleyStore.ui_helpers import card, page_header


# (title, description, route, icon); a shortcut shows only when the role may open its route.
SHORTCUTS: tuple[tuple[str, str, str, str], ...] = (
    ("Catálogo de motos", "Vitrine com modelos, cores e preços.", "/catalogo", "store"),
    ("Estoque e reservas de motos", "Unidades disponíveis, reservas e catálogo.", "/vendas", "badge-dollar-sign"),
    ("Ordens de serviço", "Abertura, andamento, peças e mão de obra.", "/workshop", "wrench"),
    ("Entradas de mercadoria", "Compras de fornecedores e estoque.", "/estoque/entradas", "package-plus"),
    ("Produtos e peças", "Catálogo de peças, preço e saldo.", "/cadastros/produtos", "boxes"),
    ("Clientes", "Pessoas e compradores.", "/cadastros/clientes", "users"),
    ("Motos de clientes", "Veículos atendidos pela oficina.", "/cadastros/motos-clientes", "bike"),
    ("Fornecedores", "Parceiros de abastecimento.", "/cadastros/fornecedores", "truck"),
    ("Funcionários", "Equipe e perfis de acesso.", "/cadastros/funcionarios", "id-card"),
    ("Financeiro", "Receitas, despesas e saldo do período.", "/financeiro", "chart-column"),
)


def shortcut_card(title: str, description: str, route: str, icon: str) -> rx.Component:
    link = rx.link(
        card(
            rx.hstack(
                rx.center(
                    rx.icon(icon, size=22, color=COLORS["on_orange"]),
                    width="2.75rem",
                    height="2.75rem",
                    min_width="2.75rem",
                    background=COLORS["orange"],
                    border_radius="4px",
                ),
                rx.vstack(
                    rx.heading(title, size="3"),
                    rx.text(description, size="2", color=COLORS["muted"]),
                    spacing="1",
                    align="start",
                ),
                align="center",
                spacing="4",
            ),
            height="100%",
            _hover={"border_color": COLORS["orange"]},
        ),
        href=route,
        underline="none",
    )
    if route in PUBLIC_ROUTES:
        return link
    return rx.cond(AuthState.allowed_routes.contains(route), link)


def dashboard() -> rx.Component:
    return page_body(
        page_header("Visão geral", f"Bem-vindo, {AuthState.display_name}. Escolha uma área para começar."),
        rx.grid(
            *[shortcut_card(*shortcut) for shortcut in SHORTCUTS],
            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
            spacing="4",
            width="100%",
        ),
    )


def admin_placeholder() -> rx.Component:
    return page_body(
        page_header("Administração", "Gestão de usuários e parâmetros do sistema: em preparação."),
    )
