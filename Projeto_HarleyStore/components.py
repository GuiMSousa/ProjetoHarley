"""Application shell: login, sidebar navigation, public shell, guard and modal overlay."""

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.styles.theme import CARD, COLORS, FONTS, GRADIENTS
from Projeto_HarleyStore.ui_helpers import card, error_callout, metal_button, primary_button


# Sidebar sections; each link is shown only when the role may enter the route
# (routes outside ROUTE_ROLES, such as "/", are open to every signed-in user).
NAV_SECTIONS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    (
        "Operação",
        (
            ("Visão geral", "/", "layout-dashboard"),
            ("Catálogo de motos", "/catalogo", "store"),
        ),
    ),
    ("Vendas", (("Estoque e reservas de motos", "/vendas", "badge-dollar-sign"),)),
    ("Oficina", (("Ordens de serviço", "/workshop", "wrench"),)),
    (
        "Estoque",
        (
            ("Entradas de mercadoria", "/estoque/entradas", "package-plus"),
            ("Produtos e peças", "/cadastros/produtos", "boxes"),
        ),
    ),
    (
        "Cadastros",
        (
            ("Clientes", "/cadastros/clientes", "users"),
            ("Motos de clientes", "/cadastros/motos-clientes", "bike"),
            ("Fornecedores", "/cadastros/fornecedores", "truck"),
            ("Funcionários", "/cadastros/funcionarios", "id-card"),
        ),
    ),
    ("Administração", (("Administração", "/admin", "shield"),)),
)
PUBLIC_ROUTES = frozenset({"/", "/catalogo"})
MOBILE_BREAKPOINT = "md"


def brand_mark(size: str = "4") -> rx.Component:
    """Text signature of the store (no trademark logo or proprietary font)."""
    return rx.hstack(
        rx.box(width="6px", height="2.25rem", background=COLORS["orange"]),
        rx.vstack(
            rx.text(
                "HARLEY STORE",
                font_family=FONTS["heading"],
                font_weight="700",
                size=size,
                letter_spacing="0.14em",
                color=COLORS["text"],
                white_space="nowrap",
            ),
            rx.text(
                "Concessionária e oficina",
                size="1",
                color=COLORS["muted"],
                text_transform="uppercase",
                letter_spacing="0.12em",
                white_space="nowrap",
            ),
            spacing="0",
            align="start",
        ),
        align="center",
        spacing="3",
    )


# ----- login -----


def login_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            brand_mark("6"),
            card(
                rx.vstack(
                    rx.heading("Acesso ao sistema", size="6"),
                    rx.text("Entre com seu usuário corporativo.", color=COLORS["muted"]),
                    rx.input(
                        placeholder="Email",
                        type="email",
                        value=AuthState.email,
                        on_change=AuthState.set_email,
                        width="100%",
                        size="3",
                    ),
                    rx.input(
                        placeholder="Senha",
                        type="password",
                        value=AuthState.password,
                        on_change=AuthState.set_password,
                        width="100%",
                        size="3",
                    ),
                    error_callout(AuthState.error_message),
                    primary_button(
                        rx.cond(AuthState.is_loading, "Validando...", "Entrar"),
                        on_click=AuthState.login,
                        disabled=AuthState.is_loading,
                        width="100%",
                        size="3",
                    ),
                    spacing="4",
                    width="100%",
                ),
                border_top=f"3px solid {COLORS['orange']}",
                width="100%",
                padding="2rem",
            ),
            rx.link("Ver catálogo de motos", href="/catalogo", color=COLORS["muted"], size="2"),
            spacing="5",
            align="center",
            width="min(100%, 26rem)",
        ),
        min_height="100vh",
        background=GRADIENTS["login"],
        padding="1.5rem",
    )


# ----- navigation -----


def _is_active(route: str) -> rx.Var:
    return AuthState.router.url.path == route


def _nav_link(label: str, route: str, icon: str) -> rx.Component:
    active = _is_active(route)
    link = rx.link(
        rx.hstack(
            rx.icon(icon, size=16),
            rx.text(label, size="2"),
            align="center",
            spacing="3",
            padding="0.55rem 0.75rem",
            border_radius="4px",
            border_left=rx.cond(active, f"3px solid {COLORS['orange']}", "3px solid transparent"),
            background=rx.cond(active, COLORS["surface"], "transparent"),
            color=rx.cond(active, COLORS["text"], COLORS["muted"]),
            _hover={"color": COLORS["text"], "background": COLORS["surface"]},
            width="100%",
        ),
        href=route,
        underline="none",
        width="100%",
    )
    if route in PUBLIC_ROUTES:
        return link
    return rx.cond(AuthState.allowed_routes.contains(route), link)


def nav_sections(*, in_drawer: bool = False) -> rx.Component:
    blocks = []
    for title, links in NAV_SECTIONS:
        items = [_nav_link(*link) for link in links]
        if in_drawer:
            items = [rx.drawer.close(item) for item in items]
        blocks.append(
            rx.vstack(
                rx.text(
                    title,
                    size="1",
                    color=COLORS["muted"],
                    text_transform="uppercase",
                    letter_spacing="0.14em",
                    padding_left="0.75rem",
                ),
                *items,
                spacing="1",
                align="stretch",
                width="100%",
            )
        )
    return rx.vstack(*blocks, spacing="5", align="stretch", width="100%")


def sidebar() -> rx.Component:
    return rx.vstack(
        brand_mark(),
        nav_sections(),
        spacing="6",
        align="stretch",
        padding="1.5rem 1rem",
        width="16.5rem",
        min_width="16.5rem",
        min_height="100vh",
        background=COLORS["graphite"],
        border_right=f"1px solid {COLORS['border']}",
        display=rx.breakpoints(initial="none", **{MOBILE_BREAKPOINT: "flex"}),
    )


def mobile_menu() -> rx.Component:
    """Drawer with the same navigation on screens narrower than the sidebar breakpoint."""
    return rx.box(
        rx.drawer.root(
            rx.drawer.trigger(
                rx.icon_button(rx.icon("menu"), variant="ghost", aria_label="Abrir menu"),
            ),
            rx.drawer.overlay(z_index="30"),
            rx.drawer.portal(
                rx.drawer.content(
                    rx.vstack(
                        brand_mark(),
                        nav_sections(in_drawer=True),
                        spacing="6",
                        align="stretch",
                        padding="1.5rem 1rem",
                    ),
                    width="17rem",
                    height="100%",
                    background=COLORS["graphite"],
                    overflow_y="auto",
                    z_index="40",
                ),
            ),
            direction="left",
        ),
        display=rx.breakpoints(initial="block", **{MOBILE_BREAKPOINT: "none"}),
    )


def top_bar() -> rx.Component:
    return rx.hstack(
        mobile_menu(),
        rx.spacer(),
        rx.vstack(
            rx.text(AuthState.display_name, size="2", color=COLORS["text"], font_weight="600"),
            rx.text(
                AuthState.employee_role,
                size="1",
                color=COLORS["orange"],
                text_transform="uppercase",
                letter_spacing="0.1em",
            ),
            spacing="0",
            align="end",
        ),
        metal_button(rx.icon("log-out", size=14), "Sair", on_click=AuthState.logout, size="2"),
        width="100%",
        align="center",
        spacing="4",
        padding="0.9rem 1.5rem",
        background=COLORS["graphite"],
        border_bottom=f"1px solid {COLORS['border']}",
    )


def app_shell(content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            top_bar(),
            content,
            align="stretch",
            spacing="0",
            width="100%",
            min_width="0",
            min_height="100vh",
            background=COLORS["black"],
        ),
        align="start",
        spacing="0",
        width="100%",
        min_height="100vh",
        background=COLORS["black"],
    )


def public_shell(content: rx.Component) -> rx.Component:
    """Shell of pages open to visitors (no sidebar, link to the staff area)."""
    return rx.vstack(
        rx.hstack(
            rx.link(brand_mark(), href="/catalogo", underline="none"),
            rx.spacer(),
            rx.cond(
                AuthState.is_authenticated,
                rx.link(metal_button("Painel", size="2"), href="/"),
                rx.link(
                    metal_button(
                        rx.icon("lock", size=14),
                        rx.text("Área do colaborador", display=rx.breakpoints(initial="none", sm="inline")),
                        rx.text("Entrar", display=rx.breakpoints(initial="inline", sm="none")),
                        size="2",
                    ),
                    href="/login",
                ),
            ),
            width="100%",
            align="center",
            padding="1rem 1.5rem",
            background=COLORS["graphite"],
            border_bottom=f"1px solid {COLORS['border']}",
        ),
        content,
        spacing="0",
        align="stretch",
        width="100%",
        min_height="100vh",
        background=COLORS["black"],
    )


def access_denied_page() -> rx.Component:
    return rx.center(
        card(
            rx.vstack(
                rx.icon("lock", size=32, color=COLORS["orange"]),
                rx.heading("Acesso negado", size="6"),
                rx.text("Seu perfil não possui permissão para acessar esta área.", color=COLORS["muted"]),
                rx.link(metal_button("Voltar para a visão geral"), href="/"),
                align="center",
                spacing="4",
            ),
            border_top=f"3px solid {COLORS['orange']}",
            padding="2rem",
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


def page_body(*children: rx.Component, **props) -> rx.Component:
    """Standard padding and rhythm of a module page inside the shell."""
    return rx.vstack(
        *children,
        **{"align": "stretch", "spacing": "5", "padding": rx.breakpoints(initial="1rem", md="2rem"), "width": "100%", **props},
    )


def modal_panel(*children: rx.Component, width: str = "min(100%, 34rem)") -> rx.Component:
    """Centered overlay panel with a blurred backdrop, shared by forms and detail views."""
    return rx.box(
        rx.vstack(
            *children,
            align="stretch",
            spacing="4",
            width=width,
            max_height="90vh",
            overflow_y="auto",
            padding="1.5rem",
            border_top=f"3px solid {COLORS['orange']}",
            **CARD,
        ),
        position="fixed",
        inset="0",
        z_index="20",
        display="flex",
        align_items="center",
        justify_content="center",
        padding="1rem",
        background=COLORS["overlay"],
        backdrop_filter="blur(8px)",
    )
