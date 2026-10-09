"""Busy states must reach the browser before the Xano call (saneamento pós-Change 9).

Reflex sends state to the frontend only when a handler finishes or yields. A handler that sets
``is_saving = True`` and calls Xano without yielding never shows "Salvando…" nor disables the
button while the request runs, so a second click is queued and submitted again.
"""

import inspect
import unittest

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.cadastros_state import CadastrosState
from Projeto_HarleyStore.catalogo_state import CatalogoState
from Projeto_HarleyStore.entradas_state import EntradasState
from Projeto_HarleyStore.financeiro_state import FinanceiroState
from Projeto_HarleyStore.vendas_state import VendasState
from Projeto_HarleyStore.workshop_state import WorkshopState


BUSY_HANDLERS = {
    AuthState: ("login",),
    CadastrosState: (
        "load_clientes",
        "load_motos_clientes",
        "load_produtos",
        "load_fornecedores",
        "load_funcionarios",
        "save_form",
        "deactivate",
    ),
    CatalogoState: ("load_catalogo",),
    EntradasState: ("load_entradas", "open_detail", "save_entrada"),
    FinanceiroState: ("load_financeiro", "aplicar_periodo", "usar_atalho"),
    VendasState: (
        "load_vendas",
        "open_detail",
        "confirm_reserva",
        "confirm_cancelamento",
        "confirm_venda",
        "save_modelo",
        "toggle_modelo_ativo",
        "save_moto",
    ),
    WorkshopState: (
        "load_ordens",
        "open_detail",
        "save_os",
        "confirm_transition",
        "save_item",
        "confirm_remove_item",
    ),
}


class LoadingStateTests(unittest.TestCase):
    def test_submit_and_load_handlers_yield_before_calling_xano(self):
        for state, names in BUSY_HANDLERS.items():
            for name in names:
                with self.subTest(handler=f"{state.__name__}.{name}"):
                    self.assertTrue(inspect.isgeneratorfunction(getattr(state, name).fn))


if __name__ == "__main__":
    unittest.main()
