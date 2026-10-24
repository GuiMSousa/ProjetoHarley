import re
import unittest
from pathlib import Path

import reflex as rx

from Projeto_HarleyStore.feedback import TOAST_POSITION, toast_error, toast_success
from Projeto_HarleyStore.styles.theme import STATUS_COLORS
from Projeto_HarleyStore.ui_helpers import (
    card,
    danger_button,
    empty_state,
    error_callout,
    labeled,
    metal_button,
    operation_is_blocked,
    page_header,
    primary_button,
    section_title,
    stat_tile,
    status_badge,
    swatch,
)


PACKAGE = Path(__file__).parents[1] / "Projeto_HarleyStore"


def toast_expression(spec) -> str:
    return str({str(name): value for name, value in spec.args}["function"])


class SharedHelpersTests(unittest.TestCase):
    def test_loading_and_mutation_flags_block_reentrant_operations(self):
        self.assertTrue(operation_is_blocked(True, False, False))
        self.assertTrue(operation_is_blocked(False, True, False))
        self.assertTrue(operation_is_blocked(False, False, True))
        self.assertFalse(operation_is_blocked(False, False, False))

    def test_toasts_share_level_and_position(self):
        for helper, level in ((toast_error, "error"), (toast_success, "success")):
            with self.subTest(level=level):
                expression = toast_expression(helper("Saldo insuficiente"))
                self.assertIn(f'["{level}"]("Saldo insuficiente"', expression)
                self.assertIn(f'"{TOAST_POSITION}"', expression)

    def test_components_build(self):
        status = rx.Var.create("ABERTA")
        components = (
            labeled("Quantidade", rx.input()),
            error_callout(rx.Var.create("Erro")),
            page_header("Oficina", "Ordens de serviço", primary_button("Nova OS")),
            section_title("Itens"),
            card(rx.text("x")),
            metal_button("Voltar"),
            danger_button("Remover"),
            empty_state("Nada aqui."),
            stat_tile("Total", "R$ 1,00", accent=True),
            status_badge(status, rx.Var.create("Aberta")),
            swatch("#0B0B0B", "Vivid Black", selected=True),
        )
        for component in components:
            with self.subTest(component=type(component).__name__):
                self.assertIsInstance(component, rx.Component)

    def test_swatch_without_a_readable_color_is_an_empty_ring(self):
        # A color typed in the Xano panel with an invalid hex is read as "": not the orange accent.
        for hex_color in ("", rx.Var.create("")):
            with self.subTest(hex_color=hex_color):
                rendered = str(swatch(hex_color, "Preto", on_click=rx.console_log("x")))
                self.assertIn("transparent", rendered)

    def test_status_badge_covers_every_status_with_its_palette(self):
        rendered = str(status_badge(rx.Var.create("RESERVADA"), "Reservada"))
        for name, (background, color) in STATUS_COLORS.items():
            with self.subTest(status=name):
                self.assertIn(name, rendered)
                self.assertIn(background, rendered)
                self.assertIn(color, rendered)

    def test_pages_use_the_shared_status_badge(self):
        for path in PACKAGE.rglob("*.py"):
            relative = path.relative_to(PACKAGE).as_posix()
            with self.subTest(path=relative):
                if relative != "ui_helpers.py":
                    self.assertIsNone(
                        re.search(r"^def status_badge\(", path.read_text(encoding="utf-8"), re.MULTILINE)
                    )

    def test_helpers_are_defined_once_and_toasts_go_through_feedback(self):
        for path in PACKAGE.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            relative = path.relative_to(PACKAGE).as_posix()
            with self.subTest(path=relative):
                if relative != "ui_helpers.py":
                    self.assertIsNone(
                        re.search(r"^def (labeled|error_callout|operation_is_blocked)\(", content, re.MULTILINE)
                    )
                if relative != "feedback.py":
                    self.assertNotIn("rx.toast(", content)


if __name__ == "__main__":
    unittest.main()
