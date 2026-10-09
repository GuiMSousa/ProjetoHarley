"""Application entry point: pages, routes and global stylesheets."""

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.cadastros_pages import cadastro_page
from Projeto_HarleyStore.cadastros_state import CadastrosState
from Projeto_HarleyStore.catalogo_pages import catalogo_page
from Projeto_HarleyStore.catalogo_state import CATALOGO_ROUTE, CatalogoState
from Projeto_HarleyStore.components import app_shell, guarded_page, login_page
from Projeto_HarleyStore.dashboard_pages import admin_placeholder, dashboard
from Projeto_HarleyStore.entradas_pages import entradas_page
from Projeto_HarleyStore.entradas_state import ENTRADAS_ROUTE, EntradasState
from Projeto_HarleyStore.financeiro_pages import financeiro_page
from Projeto_HarleyStore.financeiro_state import FINANCEIRO_ROUTE, FinanceiroState
from Projeto_HarleyStore.styles.theme import COLORS, GOOGLE_FONTS_URL
from Projeto_HarleyStore.vendas_pages import vendas_page
from Projeto_HarleyStore.vendas_state import VENDAS_ROUTE, VendasState
from Projeto_HarleyStore.workshop_pages import workshop_page
from Projeto_HarleyStore.workshop_state import WORKSHOP_ROUTE, WorkshopState


def index() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        app_shell(dashboard()),
        login_page(),
    )


def login() -> rx.Component:
    return login_page()


app = rx.App(
    stylesheets=[GOOGLE_FONTS_URL, "/harley.css"],
    # Mobile browser chrome matches the app background.
    head_components=[rx.el.meta(name="theme-color", content=COLORS["black"])],
)
app.add_page(index, route="/", title="Harley Store", on_load=AuthState.restore_session)
app.add_page(login, route="/login", title="Entrar | Harley Store")
app.add_page(
    catalogo_page,
    route=CATALOGO_ROUTE,
    title="Catálogo de motos | Harley Store",
    on_load=[AuthState.restore_session, CatalogoState.load_catalogo],
)
app.add_page(
    lambda: guarded_page(admin_placeholder(), "/admin"),
    route="/admin",
    title="Administração | Harley Store",
    on_load=AuthState.restore_session,
)
app.add_page(
    workshop_page,
    route=WORKSHOP_ROUTE,
    title="Oficina | Harley Store",
    on_load=[AuthState.restore_session, WorkshopState.load_ordens],
)
app.add_page(
    lambda: cadastro_page("clientes"),
    route="/cadastros/clientes",
    title="Clientes | Harley Store",
    on_load=[AuthState.restore_session, CadastrosState.load_clientes],
)
app.add_page(
    lambda: cadastro_page("motos_clientes"),
    route="/cadastros/motos-clientes",
    title="Motos de clientes | Harley Store",
    on_load=[AuthState.restore_session, CadastrosState.load_motos_clientes],
)
app.add_page(
    lambda: cadastro_page("produtos"),
    route="/cadastros/produtos",
    title="Produtos e peças | Harley Store",
    on_load=[AuthState.restore_session, CadastrosState.load_produtos],
)
app.add_page(
    lambda: cadastro_page("fornecedores"),
    route="/cadastros/fornecedores",
    title="Fornecedores | Harley Store",
    on_load=[AuthState.restore_session, CadastrosState.load_fornecedores],
)
app.add_page(
    lambda: cadastro_page("funcionarios"),
    route="/cadastros/funcionarios",
    title="Funcionários | Harley Store",
    on_load=[AuthState.restore_session, CadastrosState.load_funcionarios],
)
app.add_page(
    entradas_page,
    route=ENTRADAS_ROUTE,
    title="Entradas de mercadoria | Harley Store",
    on_load=[AuthState.restore_session, EntradasState.load_entradas],
)
app.add_page(
    vendas_page,
    route=VENDAS_ROUTE,
    title="Vendas de motos | Harley Store",
    on_load=[AuthState.restore_session, VendasState.load_vendas],
)
app.add_page(
    financeiro_page,
    route=FINANCEIRO_ROUTE,
    title="Financeiro | Harley Store",
    on_load=[AuthState.restore_session, FinanceiroState.load_financeiro],
)
