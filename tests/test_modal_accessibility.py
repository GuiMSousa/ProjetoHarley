"""Change 14: every modal is a Radix dialog that Esc closes through the same handler as "Fechar"."""

import ast
import unittest
from pathlib import Path

import reflex as rx
from reflex.state import State

from Projeto_HarleyStore.balcao_state import BalcaoState
from Projeto_HarleyStore.cadastros_state import CadastrosState
from Projeto_HarleyStore.catalogo_state import CatalogoState
from Projeto_HarleyStore.components import MODAL_FOCUS_SCRIPT, modal_panel
from Projeto_HarleyStore.entradas_state import EntradasState
from Projeto_HarleyStore.ui_helpers import modal_header
from Projeto_HarleyStore.vendas_state import VendasState
from Projeto_HarleyStore.workshop_state import WorkshopState

from tests.event_runner import run_event

APP_DIR = Path(__file__).resolve().parents[1] / "Projeto_HarleyStore"

# Esc handler -> (state, values while the modal is open, values once it is closed).
RESETS = {
    "BalcaoState.fechar_confirmacao": (BalcaoState, {"confirm_open": True}, {"confirm_open": False}),
    "BalcaoState.fechar_recibo": (
        BalcaoState,
        {"recibo": {"numero": "7"}, "recibo_itens": [{"descricao": "Filtro"}]},
        {"recibo": {}, "recibo_itens": []},
    ),
    "CadastrosState.close_form": (CadastrosState, {"form_open": True, "form_error": "x"}, {"form_open": False, "form_error": ""}),
    "CatalogoState.close_detail": (CatalogoState, {"detalhe_id": "1"}, {"detalhe_id": ""}),
    "EntradasState.close_detail": (EntradasState, {"detail_open": True}, {"detail_open": False}),
    "EntradasState.close_form": (EntradasState, {"form_open": True, "form_error": "x"}, {"form_open": False, "form_error": ""}),
    "VendasState.close_detail": (VendasState, {"detail_open": True}, {"detail_open": False}),
    "VendasState.close_reserva": (VendasState, {"reserva_moto_id": "9", "reserva_error": "x"}, {"reserva_moto_id": "", "reserva_error": ""}),
    "VendasState.close_cancelamento": (VendasState, {"cancel_moto_id": "9", "cancel_error": "x"}, {"cancel_moto_id": "", "cancel_error": ""}),
    "VendasState.close_venda": (VendasState, {"venda_moto_id": "9", "venda_error": "x"}, {"venda_moto_id": "", "venda_error": ""}),
    "VendasState.close_modelo_form": (VendasState, {"modelo_form_open": True, "modelo_error": "x"}, {"modelo_form_open": False, "modelo_error": ""}),
    "VendasState.close_moto_form": (VendasState, {"moto_form_open": True, "moto_error": "x"}, {"moto_form_open": False, "moto_error": ""}),
    "WorkshopState.close_detail": (WorkshopState, {"detail_open": True}, {"detail_open": False}),
    "WorkshopState.close_form": (WorkshopState, {"form_open": True, "form_error": "x"}, {"form_open": False, "form_error": ""}),
}


def walk(component):
    yield component
    for child in component.children:
        yield from walk(child)


def modal_calls() -> dict[str, tuple[str | None, str | None]]:
    """Every ``modal_panel`` call in the app: {"file:line": (its on_close, its modal_header's on_close)}."""
    calls = {}
    for path in sorted(APP_DIR.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "modal_panel":
                header = node.args[0] if node.args else None
                header_kwargs = {}
                if isinstance(header, ast.Call) and getattr(header.func, "id", None) == "modal_header":
                    header_kwargs = {k.arg: ast.unparse(k.value) for k in header.keywords}
                panel_kwargs = {k.arg: ast.unparse(k.value) for k in node.keywords}
                calls[f"{path.name}:{node.lineno}"] = (panel_kwargs.get("on_close"), header_kwargs.get("on_close"))
    return calls


def substate(state_class):
    return State(_reflex_internal_init=True).get_substate(state_class.get_full_name().split("."))


class ModalPanelTests(unittest.TestCase):
    def setUp(self):
        self.modal = modal_panel(
            modal_header("Título", on_close=CatalogoState.close_detail),
            rx.text("corpo"),
            on_close=CatalogoState.close_detail,
        )
        self.content = self.modal.children[0]

    def test_open_radix_dialog_with_aria(self):
        self.assertEqual(type(self.modal).__name__, "DialogRoot")
        self.assertEqual(str(self.modal.open), "true")
        self.assertEqual(type(self.content).__name__, "DialogContent")
        self.assertEqual(self.content.custom_attrs.get("aria-modal"), "true")
        tipos = [type(c).__name__ for c in walk(self.modal)]
        # Title (aria-labelledby) and description (aria-describedby) are wired by the Radix dialog.
        self.assertIn("DialogTitle", tipos)
        self.assertIn("DialogDescription", tipos)

    def test_description_is_for_screen_readers_only(self):
        description = next(c for c in walk(self.modal) if type(c).__name__ == "DialogDescription")
        self.assertIn("sr-only", str(description.class_name))
        self.assertIn("Pressione Esc para fechar.", str(description.children[0].contents))

    def test_esc_runs_on_close_and_outside_clicks_are_ignored(self):
        esc = self.content.event_triggers["on_escape_key_down"].events
        self.assertEqual([spec.handler.fn for spec in esc], [CatalogoState.close_detail.fn])
        fora = self.content.event_triggers["on_interact_outside"].events
        self.assertTrue(fora[0].event_actions.get("preventDefault"))
        # Focus goes back to the control that opened the dialog (the browser smoke checks the effect).
        self.assertIn("on_close_auto_focus", self.content.event_triggers)

    def test_header_title_names_the_dialog_and_fechar_closes(self):
        header = modal_header("Título", on_close=CatalogoState.close_detail)
        self.assertEqual(type(header.children[0]).__name__, "DialogTitle")
        fechar = next(c for c in walk(header) if type(c).__name__ == "Button")
        self.assertEqual([s.handler.fn for s in fechar.event_triggers["on_click"].events], [CatalogoState.close_detail.fn])


class FocusScriptTests(unittest.TestCase):
    def test_app_head_keeps_the_focus_listener(self):
        app = ast.parse((APP_DIR / "Projeto_HarleyStore.py").read_text(encoding="utf-8"))
        rx_app = next(n for n in ast.walk(app) if isinstance(n, ast.Call) and ast.unparse(n.func) == "rx.App")
        head = next(k.value for k in rx_app.keywords if k.arg == "head_components")
        self.assertIn("rx.script(MODAL_FOCUS_SCRIPT)", [ast.unparse(item) for item in head.elts])

    def test_listener_ignores_focus_while_a_modal_is_open(self):
        # rx.select options live in a portal outside the dialog: they must not become the return target.
        self.assertIn("!document.querySelector('[role=dialog][aria-modal=true]')", MODAL_FOCUS_SCRIPT)


class EscWiringTests(unittest.TestCase):
    def test_every_modal_closes_on_esc_with_the_handler_of_its_fechar(self):
        calls = modal_calls()
        self.assertGreaterEqual(len(calls), 14)
        for local, (painel, cabecalho) in calls.items():
            with self.subTest(modal=local):
                self.assertIsNotNone(cabecalho, "o modal deve começar com modal_header")
                self.assertEqual(painel, cabecalho)

    def test_every_esc_handler_has_a_reset_case(self):
        self.assertEqual({painel for painel, _ in modal_calls().values()}, set(RESETS))


class ResetTests(unittest.TestCase):
    def test_esc_handler_resets_its_modal(self):
        for nome, (state_class, aberto, fechado) in RESETS.items():
            with self.subTest(handler=nome):
                state = substate(state_class)
                for campo, valor in aberto.items():
                    setattr(state, campo, valor)
                run_event(getattr(state_class, nome.split(".")[1]), state)
                self.assertEqual({campo: getattr(state, campo) for campo in fechado}, fechado)

    def test_esc_keeps_the_counter_sale_open_while_it_is_being_recorded(self):
        state = substate(BalcaoState)
        state.confirm_open, state.is_selling = True, True
        run_event(BalcaoState.fechar_confirmacao, state)
        self.assertTrue(state.confirm_open)


if __name__ == "__main__":
    unittest.main()
