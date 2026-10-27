"""Opt-in browser smoke: the public showroom, its photo carousel and the login gate.

Start the app first (``reflex run --env prod --single-port --backend-port 3100``), then run
``HARLEY_BROWSER_URL=http://localhost:3100 python -m pytest -m browser``. It drives the
installed Microsoft Edge (``channel="msedge"``), never downloads a browser and never signs in;
the showroom reads the public catalog of the Xano workspace configured in ``.env``.
"""

import os
import unittest

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("HARLEY_BROWSER_URL", "").rstrip("/")
TIMEOUT_MS = 20_000
expect.set_options(timeout=TIMEOUT_MS)

pytestmark = pytest.mark.browser


@unittest.skipUnless(BASE_URL, "HARLEY_BROWSER_URL não definido: smoke de navegador ignorado.")
class BrowserSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        # A page of its own context: no cookies or session leak between tests. Navigation waits
        # only for the DOM (the full "load" waits for every photo); locators wait for the UI.
        self.page = self.browser.new_page()
        self.page.set_default_timeout(TIMEOUT_MS)
        self.errors: list[str] = []
        self.page.on("console", lambda msg: msg.type == "error" and self.errors.append(msg.text))
        self.page.on("pageerror", lambda exc: self.errors.append(str(exc)))
        self.addCleanup(self.page.close)

    def assert_no_browser_errors(self):
        self.assertEqual(self.errors, [], "erros no console do navegador")

    def test_showroom_opens_a_model_and_cycles_its_photos(self):
        page = self.page
        page.goto(f"{BASE_URL}/catalogo", wait_until="domcontentloaded")
        page.get_by_label("Buscar modelo").wait_for()
        page.get_by_role("button", name="Detalhes", exact=True).first.click()

        dialog = page.get_by_role("dialog")
        foto = dialog.get_by_role("img").first
        foto.wait_for()
        # Change 17: every photo comes from Xano (or is the embedded neutral image), never a local file.
        self.assertRegex(foto.get_attribute("src"), r"^(https?://|data:image/svg\+xml,)")
        self.assert_no_browser_errors()
        proxima = dialog.get_by_role("button", name="Próxima foto")
        if not proxima.count():
            self.skipTest("o primeiro modelo tem uma foto só: carrossel sem setas")
        # Each click round-trips through the Reflex websocket: expect() retries until it lands.
        primeira = foto.get_attribute("src")
        proxima.click()
        expect(foto).not_to_have_attribute("src", primeira)
        expect(dialog.get_by_role("button", name="Ver foto 2")).to_have_attribute("aria-current", "true")
        dialog.get_by_role("button", name="Foto anterior").click()
        expect(foto).to_have_attribute("src", primeira)
        self.assert_no_browser_errors()

    def test_detail_dialog_traps_focus_names_itself_and_closes_on_esc(self):
        page = self.page
        page.goto(f"{BASE_URL}/catalogo", wait_until="domcontentloaded")
        detalhes = page.get_by_role("button", name="Detalhes", exact=True).first
        detalhes.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_have_attribute("aria-modal", "true")

        dentro = "() => document.querySelector('[role=dialog]').contains(document.activeElement)"
        expect(dialog.get_by_role("button", name="Fechar")).to_be_focused()  # initial focus: its first control
        for tecla in ["Tab"] * 12 + ["Shift+Tab"] * 12:
            page.keyboard.press(tecla)
            self.assertTrue(page.evaluate(dentro), f"o foco saiu do diálogo com {tecla}")

        for atributo in ("aria-labelledby", "aria-describedby"):
            alvo = dialog.get_attribute(atributo)
            self.assertTrue(alvo, atributo)
            self.assertTrue(page.locator(f"[id='{alvo}']").inner_text().strip(), atributo)

        page.mouse.click(5, 5)  # the overlay: a click outside never closes the dialog
        expect(dialog).to_be_visible()
        # An rx.select option takes focus in a portal outside the dialog and then leaves the page;
        # it must not become the control that gets focus back when the dialog closes.
        page.evaluate(
            "() => { const opcao = document.createElement('div'); document.body.appendChild(opcao);"
            " opcao.dispatchEvent(new FocusEvent('focusin', {bubbles: true})); opcao.remove(); }"
        )
        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        expect(detalhes).to_be_focused()
        self.assert_no_browser_errors()

    def test_protected_route_without_session_shows_the_login_form(self):
        page = self.page
        page.goto(f"{BASE_URL}/vendas", wait_until="domcontentloaded")
        expect(page.get_by_label("Email")).to_be_visible()
        expect(page.get_by_label("Senha")).to_be_visible()
        expect(page.get_by_role("button", name="Detalhes")).to_have_count(0)
        self.assert_no_browser_errors()


if __name__ == "__main__":
    unittest.main()
