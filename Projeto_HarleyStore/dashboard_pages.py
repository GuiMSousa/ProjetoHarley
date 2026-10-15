"""Overview page (/): executive KPI cards by role and the action shortcuts (Change 12)."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.components import PUBLIC_ROUTES, page_body
from Projeto_HarleyStore.dashboard_state import DashboardState
from Projeto_HarleyStore.styles.theme import CARD_HOVER, COLORS, RADII
from Projeto_HarleyStore.ui_helpers import card, error_callout, page_header, section_title


# (key, title, icon) of the KPI cards; dashboard_state.KPI_ROLES decides who sees each one.
KPI_CARDS: tuple[tuple[str, str, str], ...] = (
    ("faturamento", "Faturamento do mês", "chart-column"),
    ("motos", "Motos em estoque", "bike"),
    ("os", "Ordens de serviço ativas", "wrench"),
    ("balcao", "Vendas de balcão", "shopping-cart"),
)


# (title, description, route, icon); a shortcut shows only when the role may open its route.
SHORTCUTS: tuple[tuple[str, str, str, str], ...] = (
    ("Catálogo de motos", "Vitrine com modelos, cores e preços.", "/catalogo", "store"),
    ("Estoque e reservas de motos", "Unidades disponíveis, reservas e catálogo.", "/vendas", "badge-dollar-sign"),
    ("Balcão", "Venda de peças a clientes ou consumidor final.", "/balcao", "shopping-cart"),
    ("Ordens de serviço", "Abertura, andamento, peças e mão de obra.", "/workshop", "wrench"),
    ("Entradas de mercadoria", "Compras de fornecedores e estoque.", "/estoque/entradas", "package-plus"),
    ("Produtos e peças", "Catálogo de peças, preço e saldo.", "/cadastros/produtos", "boxes"),
    ("Clientes", "Pessoas e compradores.", "/cadastros/clientes", "users"),
    ("Motos de clientes", "Veículos atendidos pela oficina.", "/cadastros/motos-clientes", "bike"),
    ("Fornecedores", "Parceiros de abastecimento.", "/cadastros/fornecedores", "truck"),
    ("Funcionários", "Equipe e perfis de acesso.", "/cadastros/funcionarios", "id-card"),
    ("Financeiro", "Receitas, despesas e saldo do período.", "/financeiro", "chart-column"),
)


def kpi_card(key: str, title: str, icon: str) -> rx.Component:
    value = rx.cond(
        DashboardState.is_loading_kpis,
        "…",
        rx.cond(DashboardState.kpis.contains(key), DashboardState.kpis[key], "—"),
    )
    detail = rx.cond(DashboardState.kpis.contains(f"{key}_detalhe"), DashboardState.kpis[f"{key}_detalhe"], "")
    return rx.cond(
        DashboardState.kpis_do_perfil.contains(key),
        card(
            rx.vstack(
                rx.hstack(
                    rx.text(title, size="1", color=COLORS["muted"], text_transform="uppercase", letter_spacing="0.08em"),
                    rx.spacer(),
                    rx.icon(icon, size=18, color=COLORS["orange"], aria_hidden="true"),
                    width="100%",
                    align="center",
                ),
                rx.text(value, font_weight="700", size="7", color=COLORS["text"]),
                rx.text(detail, size="1", color=COLORS["muted"]),
                spacing="2",
                align="start",
            ),
            border_top=f"2px solid {COLORS['orange']}",
            height="100%",
        ),
    )


def shortcut_card(title: str, description: str, route: str, icon: str) -> rx.Component:
    link = rx.link(
        card(
            rx.hstack(
                rx.center(
                    rx.icon(icon, size=22, color=COLORS["orange"], aria_hidden="true"),
                    width="2.75rem",
                    height="2.75rem",
                    min_width="2.75rem",
                    background=COLORS["graphite"],
                    border=f"1px solid {COLORS['orange']}",
                    border_radius=RADII["sm"],
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
            **CARD_HOVER,
        ),
        href=route,
        underline="none",
    )
    if route in PUBLIC_ROUTES:
        return link
    return rx.cond(AuthState.allowed_routes.contains(route), link)


def dashboard() -> rx.Component:
    return page_body(
        page_header("Visão geral", f"Bem-vindo, {AuthState.display_name}."),
        error_callout(DashboardState.kpi_error),
        rx.grid(
            *[kpi_card(*kpi) for kpi in KPI_CARDS],
            columns=rx.breakpoints(initial="1", sm="2", lg="4"),
            spacing="4",
            width="100%",
        ),
        section_title("Ações"),
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
