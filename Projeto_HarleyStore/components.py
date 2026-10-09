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
    (
        "Vendas",
        (
            ("Estoque e reservas de motos", "/vendas", "badge-dollar-sign"),
            ("Balcão", "/balcao", "shopping-cart"),
        ),
    ),
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
    ("Gestão", (("Financeiro", "/financeiro", "chart-column"),)),
    ("Administração", (("Administração", "/admin", "shield"),)),
)
PUBLIC_ROUTES = frozenset({"/", "/catalogo"})
MOBILE_BREAKPOINT = "md"

LOGO_SRC = "/HARLEY_LOGO.png"
LOGO_HEIGHT = "45px"
# Display box of the 175x135 PNG at 45px tall; the HTML width/height reserve it before the
# image loads, so the header never shifts.
LOGO_BOX = {"width": "58", "height": "45"}
# Shared height of the sidebar brand area and the top bars, so their bottom borders form one line.
HEADER_HEIGHT = "4.5rem"
# Left inset of the nav items (3px active border + 0.75rem padding); the logo aligns with their icons.
NAV_INSET = "calc(0.75rem + 3px)"


def brand_logo() -> rx.Component:
    """Store logo (assets/HARLEY_LOGO.png: shield cut from harley-davidson-logo.webp, transparent background).

    Never taller than 45px. If the file fails to load, the alt text shows inside the same box,
    and the "HARLEY STORE" title next to it keeps the brand readable.
    """
    return rx.image(
        src=LOGO_SRC,
        alt="Harley-Davidson",
        height=LOGO_HEIGHT,
        max_height=LOGO_HEIGHT,
        width="auto",
        object_fit="contain",
        flex_shrink="0",
        overflow="hidden",
        font_size="0.625rem",
        color=COLORS["muted"],
        loading="eager",
        decoding="async",
        custom_attrs={**LOGO_BOX, "fetchPriority": "high", "translate": "no"},
    )


def brand_mark(size: str = "4", subtitle_display: str | rx.breakpoints = "block") -> rx.Component:
    """Logo followed by the store title, used by every shell (sidebar, drawer, public header, login).

    Narrow places (sidebar, drawer, public header on phones) hide the subtitle so the title fits.
    """
    return rx.hstack(
        brand_logo(),
        rx.vstack(
            rx.text(
                "HARLEY STORE",
                font_family=FONTS["heading"],
                font_weight="700",
                size=size,
                letter_spacing="0.14em",
                color=COLORS["text"],
                white_space="nowrap",
                custom_attrs={"translate": "no"},
            ),
            rx.text(
                "Concessionária e oficina",
                size="1",
                color=COLORS["muted"],
                text_transform="uppercase",
                letter_spacing="0.12em",
                white_space="nowrap",
                display=subtitle_display,
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
                        name="email",
                        aria_label="Email",
                        value=AuthState.email,
                        on_change=AuthState.set_email,
                        width="100%",
                        size="3",
                        custom_attrs={"autoComplete": "username", "spellCheck": "false"},
                    ),
                    rx.input(
                        placeholder="Senha",
                        type="password",
                        name="password",
                        aria_label="Senha",
                        value=AuthState.password,
                        on_change=AuthState.set_password,
                        width="100%",
                        size="3",
                        custom_attrs={"autoComplete": "current-password"},
                    ),
                    error_callout(AuthState.error_message),
                    primary_button(
                        rx.cond(AuthState.is_loading, "Validando…", "Entrar"),
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
            rx.icon(icon, size=16, aria_hidden="true"),
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
        # Top-left corner: logo + title, aligned with the nav icons and the top bar height.
        rx.link(
            brand_mark(subtitle_display="none"),
            href="/",
            underline="none",
            display="flex",
            align_items="center",
            height=HEADER_HEIGHT,
            min_height=HEADER_HEIGHT,
            padding_left=f"calc(1rem + {NAV_INSET})",
            padding_right="1rem",
            border_bottom=f"1px solid {COLORS['border']}",
        ),
        rx.box(nav_sections(), padding="1.5rem 1rem"),
        spacing="0",
        align="stretch",
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
                        brand_mark(subtitle_display="none"),
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
        # On narrow screens the sidebar is hidden, so the logo moves to the top-left of the bar.
        rx.link(
            brand_logo(),
            href="/",
            display=rx.breakpoints(initial="block", **{MOBILE_BREAKPOINT: "none"}),
        ),
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
        min_height=HEADER_HEIGHT,
        padding="0 1.5rem",
        background=COLORS["graphite"],
        border_bottom=f"1px solid {COLORS['border']}",
    )


MAIN_ID = "conteudo"


def skip_link() -> rx.Component:
    """First focusable element: lets keyboard users jump past the navigation (styled in harley.css).

    Reflex renders the anchor as a router link, which changes the hash without moving focus,
    so the click focuses the <main> landmark explicitly.
    """
    return rx.el.a(
        "Pular para o conteúdo",
        href=f"#{MAIN_ID}",
        on_click=rx.set_focus(MAIN_ID),
        class_name="skip-link",
    )


def main_region(content: rx.Component) -> rx.Component:
    """The page content as the <main> landmark, target of the skip link."""
    return rx.el.main(content, id=MAIN_ID, tab_index=-1, width="100%", min_width="0")


def app_shell(content: rx.Component) -> rx.Component:
    return rx.fragment(
        skip_link(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                top_bar(),
                main_region(content),
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
        ),
    )


def public_shell(content: rx.Component) -> rx.Component:
    """Shell of pages open to visitors (no sidebar, link to the staff area)."""
    return rx.vstack(
        skip_link(),
        rx.hstack(
            rx.link(
                brand_mark(subtitle_display=rx.breakpoints(initial="none", sm="block")),
                href="/catalogo",
                underline="none",
            ),
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
            min_height=HEADER_HEIGHT,
            padding="0 1.5rem",
            background=COLORS["graphite"],
            border_bottom=f"1px solid {COLORS['border']}",
        ),
        main_region(content),
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
            role="dialog",
            aria_modal="true",
            align="stretch",
            spacing="4",
            width=width,
            max_height="90vh",
            overflow_y="auto",
            # Scrolling a long form never scrolls the page behind the overlay.
            overscroll_behavior="contain",
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
