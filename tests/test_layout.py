import struct
import unittest
from pathlib import Path

from Projeto_HarleyStore.cadastros_pages import cadastro_page
from Projeto_HarleyStore.catalogo_pages import catalogo_page
from Projeto_HarleyStore.components import (
    LOGO_HEIGHT,
    LOGO_SRC,
    app_shell,
    brand_mark,
    guarded_page,
    login_page,
    public_shell,
    sidebar,
    top_bar,
)
from Projeto_HarleyStore.dashboard_pages import admin_placeholder, dashboard
from Projeto_HarleyStore.entradas_pages import entradas_page
from Projeto_HarleyStore.vendas_pages import vendas_page
from Projeto_HarleyStore.workshop_pages import workshop_page


ROOT = Path(__file__).parents[1]

# Every route registered in Projeto_HarleyStore.py, with the component that renders it.
PAGES = {
    "/": lambda: app_shell(dashboard()),
    "/login": login_page,
    "/catalogo": catalogo_page,
    "/admin": lambda: guarded_page(admin_placeholder(), "/admin"),
    "/workshop": workshop_page,
    "/cadastros/clientes": lambda: cadastro_page("clientes"),
    "/cadastros/motos-clientes": lambda: cadastro_page("motos_clientes"),
    "/cadastros/produtos": lambda: cadastro_page("produtos"),
    "/cadastros/fornecedores": lambda: cadastro_page("fornecedores"),
    "/cadastros/funcionarios": lambda: cadastro_page("funcionarios"),
    "/estoque/entradas": entradas_page,
    "/vendas": vendas_page,
}


class LogoTests(unittest.TestCase):
    def test_logo_asset_is_a_png_served_from_assets(self):
        self.assertEqual(LOGO_SRC, "/HARLEY_LOGO.png")
        self.assertEqual(LOGO_HEIGHT, "45px")
        data = (ROOT / "assets" / "HARLEY_LOGO.png").read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertGreaterEqual(height, 90)  # sharp at 45px on 2x screens
        self.assertEqual(data[25], 6)  # IHDR colour type 6 = RGBA: transparent background
        self.assertLess(len(data), 100_000)

    def test_brand_and_headers_carry_the_logo(self):
        for name, component in (
            ("brand_mark", brand_mark()),
            ("sidebar", sidebar()),
            ("top_bar (mobile)", top_bar()),
            ("public_shell", public_shell(login_page())),
            ("login_page", login_page()),
        ):
            with self.subTest(component=name):
                rendered = str(component)
                self.assertIn(LOGO_SRC, rendered)
                self.assertIn(LOGO_HEIGHT, rendered)

    def test_every_route_shows_the_logo(self):
        registered = (ROOT / "Projeto_HarleyStore" / "Projeto_HarleyStore.py").read_text(encoding="utf-8")
        self.assertEqual(registered.count("app.add_page("), len(PAGES))
        for route, page in PAGES.items():
            with self.subTest(route=route):
                self.assertIn(LOGO_SRC, str(page()))


if __name__ == "__main__":
    unittest.main()
