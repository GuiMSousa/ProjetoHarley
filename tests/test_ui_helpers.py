import re
import unittest
from pathlib import Path

import reflex as rx

from Projeto_HarleyStore.feedback import TOAST_POSITION, toast_error, toast_success
from Projeto_HarleyStore.ui_helpers import error_callout, labeled, operation_is_blocked


PACKAGE = Path(__file__).parents[1] / "Projeto_HarleyStore"


def toast_expression(spec) -> str:
    return str(dict((str(name), value) for name, value in spec.args)["function"])


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
        self.assertIsInstance(labeled("Quantidade", rx.input()), rx.Component)
        self.assertIsInstance(error_callout(rx.Var.create("Erro")), rx.Component)

    def test_helpers_are_defined_once_and_toasts_go_through_feedback(self):
        for path in PACKAGE.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            relative = path.relative_to(PACKAGE).as_posix()
            with self.subTest(path=relative):
                if relative != "ui_helpers.py":
                    self.assertIsNone(
                        re.search(r"^def (labeled|error_callout|operation_is_blocked)\(", content, re.M)
                    )
                if relative != "feedback.py":
                    self.assertNotIn("rx.toast(", content)


if __name__ == "__main__":
    unittest.main()
